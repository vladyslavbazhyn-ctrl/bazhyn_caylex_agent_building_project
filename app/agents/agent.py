import os
import sys
import time
import logging
import datetime

from typing import Annotated, TypedDict, List, Literal, Tuple

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import BaseCheckpointSaver

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("AGENT")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
SERVER_DIR = os.path.join(APP_DIR, "mcp_servers")

load_dotenv()
gq_key = os.getenv("GQ_API_KEY")


@tool
def policy_lookup(query: str) -> str:
    """Consult JewelryOps policies. Use for returns, shipping, or warranties."""
    policies = {
        "return": "Returns allowed within 30 days of purchase. VIP members get 60 days.",
        "shipping": "Standard shipping 3-5 days. Overnight available for $50.",
        "warranty": "Lifetime warranty on gemstones. 1 year on metal settings."
    }
    for key, text in policies.items():
        if key in query.lower():
            return text
    return "No specific policy found in the handbook."


@tool
def get_current_date() -> str:
    """Check today's date."""
    return datetime.datetime.today().strftime("%Y-%m-%d")


@tool
def summarize_case(key_findings: List[str], next_steps: str) -> str:
    """Use this to summarize a complex investigation before finishing."""
    return f"CASE SUMMARY:\nFindings: {'; '.join(key_findings)}\nNext Steps: {next_steps}"


async def load_mcp_tools() -> Tuple[List[BaseTool], MultiServerMCPClient]:
    """Connects to the 3 separate MCP servers using absolute paths."""

    def get_server_args(script_name: str) -> List[str]:
        return [os.path.join(SERVER_DIR, script_name)]

    client = MultiServerMCPClient({
        "crm": {
            "command": sys.executable,
            "args": get_server_args("server_crm.py"),
            "transport": "stdio",
        },
        "oms": {
            "command": sys.executable,
            "args": get_server_args("server_oms.py"),
            "transport": "stdio",
        },
        "comms": {
            "command": sys.executable,
            "args": get_server_args("server_comms.py"),
            "transport": "stdio",
        }
    })

    logger.info("Connecting to MCP Servers (CRM, OMS, Comms)...")
    tools = await client.get_tools()
    all_tools = tools + [policy_lookup, get_current_date, summarize_case]
    logger.info(f"Loaded {len(tools)} MCP tools.")
    return all_tools, client


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


def build_graph(tools: List[BaseTool], checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Builds and compiles the LangGraph agent."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=gq_key
    )
    llm_with_tools = llm.bind_tools(tools)

    # ... inside build_graph ...

    SYSTEM_INSTRUCTION = """You are the JewelryOps Support Agent.

        CORE RULES:

        1. **ONE STEP AT A TIME:** - Do NOT try to be "efficient" by guessing parameters. 
           - If you don't have an Order ID, ask for it or search for it. Do NOT invent one.
           - It is better to use 3 turns to get the right answer than 1 turn to get a wrong one.
           
        2. **DATA BLINDNESS** - You do NOT believe to one data source.
           - Make MORE THAN TWO tries to find an info, split into peaces and search by pieces if it needs.
           
        3. **BE FLEXIBLE** 
            - If it's NOT A NAME and you can't find direct coincidence try to search for the synonyms. 
            - Check ALL possible policies connected to the order items, before further thinking.

        4. **STRICT DATA RETRIEVAL:**
           - **Never** provide a policy, status, or price unless you have retrieved it from a tool.
           - If a search returns "No results", tell the user immediately. Do not pretend you found something.

        5. **HANDLE AMBIGUITY:** - If a searching returns multiple results (AMBIGUOUS_MATCH), STOP and ask the user to clarify. 
           - Do not pick randomly.

        6. **SAFETY:** 
            - Always ask for "yes/no" confirmation before using `action_` tools (refunds, emails).
            - If you don't have direct 
        
        Start by checking the date, then help the user.
        """

    def agent_node(state: AgentState) -> dict:

        time.sleep(2)  # To not hit rate limiting

        messages = state["messages"]
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_INSTRUCTION)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", END]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=checkpointer, interrupt_before=["tools"])
