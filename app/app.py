import os
import sys
import logging
import streamlit as st
import asyncio

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.agent import load_mcp_tools, build_graph, policy_lookup, summarize_case, get_current_date


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("APP")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="JewelryOps Agent (MCP)", page_icon="💎", layout="wide")
st.title("💎 JewelryOps (MCP Architecture)")


async def boot_agent():
    """Initializes the graph and tools once."""

    mcp_tools, client = await load_mcp_tools()
    all_tools = mcp_tools + [policy_lookup, summarize_case, get_current_date]
    graph = build_graph(all_tools)
    return graph, client, {t.name: t for t in all_tools}


async def run_graph(graph, inputs, config):
    """Runs the graph and yields events."""

    events = []
    async for event in graph.astream(inputs, config, stream_mode="values"):
        events.append(event)
    return events


if "graph" not in st.session_state:
    with st.spinner("Initializing 3-Server MCP Architecture..."):

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graph, client, tool_map = loop.run_until_complete(boot_agent())

        st.session_state.graph = graph
        st.session_state.mcp_client = client
        st.session_state.tools_map = tool_map
        st.success("System Online: CRM, OMS, Comms connected.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "demo_session_01"

with st.sidebar:
    st.header("Debug Context")
    if st.button("Clear Memory"):
        st.session_state.messages = []
        st.rerun()
    st.write(f"Active Thread: `{st.session_state.thread_id}`")

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    elif isinstance(msg, AIMessage):
        st.chat_message("assistant").write(msg.content)
        if msg.tool_calls:
            with st.expander("🛠️ Agent Thought Process"):
                st.json(msg.tool_calls)
    elif isinstance(msg, ToolMessage):
        with st.expander(f"💾 Tool Output: {msg.name}"):
            st.code(msg.content)

user_input = st.chat_input("How can I help?")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    with st.spinner("Thinking..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        events = loop.run_until_complete(
            run_graph(st.session_state.graph, {"messages": [HumanMessage(content=user_input)]}, config)
        )

        for event in events:
            if "messages" in event:
                msg = event["messages"][-1]
                if msg not in st.session_state.messages:
                    st.session_state.messages.append(msg)
        st.rerun()

if "graph" in st.session_state:
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    snapshot = st.session_state.graph.get_state(config)

    if snapshot.next and snapshot.next[0] == "tools":
        last_msg = snapshot.values["messages"][-1]
        tool_calls = last_msg.tool_calls

        sensitive = [t for t in tool_calls if t["name"].startswith("action_")]

        if sensitive:
            st.warning(f"⚠️ **APPROVAL REQUIRED**: The agents wants to execute: `{[t['name'] for t in sensitive]}`")
            col1, col2 = st.columns(2)

            if col1.button("✅ Approve Action"):
                with st.spinner("Processing Approved Action..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Resume with None (Go ahead)
                    events = loop.run_until_complete(run_graph(st.session_state.graph, None, config))
                    for event in events:
                        if "messages" in event:
                            st.session_state.messages.append(event["messages"][-1])
                    st.rerun()

            if col2.button("❌ Deny"):
                st.error("Action Denied.")
                st.stop()
        else:

            with st.spinner("Running queries..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                events = loop.run_until_complete(run_graph(st.session_state.graph, None, config))
                for event in events:
                    if "messages" in event:
                        msg = event["messages"][-1]
                        if msg not in st.session_state.messages:
                            st.session_state.messages.append(msg)
                st.rerun()
