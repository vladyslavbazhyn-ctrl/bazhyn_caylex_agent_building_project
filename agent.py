import os
import sys
import time
import datetime

from typing import Annotated, TypedDict, List

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()
gcp_key = os.getenv("GCP_API_KEY")


@tool
def policy_lookup(query: str):
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
def summarize_case(key_findings: List[str], next_steps: str):
    """Use this to summarize a complex investigation before finishing."""
    return f"CASE SUMMARY:\nFindings: {'; '.join(key_findings)}\nNext Steps: {next_steps}"


async def load_mcp_tools():
    """Connects to the 3 separate MCP servers."""
    client = MultiServerMCPClient({
        "crm": {
            "command": sys.executable,
            "args": ["server_crm.py"],
            "transport": "stdio",
        },
        "oms": {
            "command": sys.executable,
            "args": ["server_oms.py"],
            "transport": "stdio",
        },
        "comms": {
            "command": sys.executable,
            "args": ["server_comms.py"],
            "transport": "stdio",
        }
    })

    print("🔌 Connecting to MCP Servers (CRM, OMS, Comms)...")
    tools = await client.get_tools()
    print(f"✅ Loaded {len(tools)} MCP tools.")
    return tools, client


def build_graph(tools: tool) -> CompiledStateGraph:
    class AgentState(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest", temperature=0, api_key=gcp_key
    )
    llm_with_tools = llm.bind_tools(tools)

    SYSTEM_INSTRUCTION = """You are the JewelryOps Senior Support Agent.

    1. **NO GUESSING:** You must strictly retrieve IDs and status from the database. 
       - Never invent an Order ID or Policy.
       - If a tool returns "No results", state that clearly.

    2. **TRIANGULATE DATA:** Do not rely on a single data point. Cross-reference CRM data with OMS data to ensure accuracy.

    3. **HANDLE AMBIGUITY:** If a search (e.g., for "Alice") returns an "AMBIGUOUS_MATCH" error, you MUST stop and ask the user to clarify. Do not guess.

    4. **DEEP DIVE:** When investigating an issue, be exhaustive. 

    5. **SAFETY FIRST:** Always ask for confirmation before taking actions with side effects (refunds, emails, or saving notes).

    Do not skip steps. Be thorough and professional.
    """

    def agent_node(state: AgentState) -> dict:
        time.sleep(2)  # Free version of gemini has limit calls per second.

        messages = state["messages"]
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_INSTRUCTION)] + messages
        return {"messages": [llm_with_tools.invoke(messages)]}

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=MemorySaver(), interrupt_before=["tools"])
