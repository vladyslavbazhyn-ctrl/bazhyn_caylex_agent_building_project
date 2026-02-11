import os
import sys
import logging
import uuid
import asyncio
import streamlit as st

from langgraph.checkpoint.memory import MemorySaver
from helpers.app_helpers import get_graph_and_client, reset_memory, parse_response, run_async

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="JewelryOps Agent", page_icon="💎", layout="wide")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("APP")


if "memory" not in st.session_state:
    st.session_state.memory = MemorySaver()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

graph, mcp_client = get_graph_and_client()

st.title("💎 Jewelry Support Agent")
st.caption(f"Session ID: {st.session_state.thread_id}")

with st.sidebar:
    st.header("Controls")
    if st.button("🧹 Clear Memory", on_click=reset_memory):
        st.success("Memory Wiped!")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        clean_content = parse_response(msg["content"])
        st.markdown(clean_content)

if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        try:
            full_response = ""

            with st.spinner("Thinking..."):
                async def run_conversation_loop():
                    input_payload = {"messages": [("user", prompt)]}
                    config = {"configurable": {"thread_id": st.session_state.thread_id}}

                    current_input = input_payload
                    processed_tools = set()

                    step_log = []

                    with st.expander("🛠️ View Execution Steps", expanded=True):
                        step_container = st.empty()

                        while True:

                            last_msg = None

                            async for event in graph.astream(current_input, config, stream_mode="values"):

                                await asyncio.sleep(1)

                                if "messages" in event:
                                    last_msg = event["messages"][-1]

                                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                        for tool in last_msg.tool_calls:
                                            if tool['id'] not in processed_tools:
                                                args_str = str(tool['args'])

                                                if len(tool['args']) == 1:
                                                    args_str = list(tool['args'].values())[0]

                                                step_log.append(f"✅ **{tool['name']}**: `{args_str}`")
                                                processed_tools.add(tool['id'])

                                                step_container.markdown("\n\n".join(step_log))
                            if not last_msg:
                                break

                            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                sensitive_tools = [t for t in last_msg.tool_calls if t["name"].startswith("action_")]

                                if sensitive_tools:
                                    return "__REQUIRE_APPROVAL__"
                                else:
                                    current_input = None
                                    continue

                            else:
                                return last_msg.content


                full_response = run_async(run_conversation_loop())

            if full_response == "__REQUIRE_APPROVAL__":
                st.warning("⚠️ **APPROVAL REQUIRED**: The agent wants to perform a sensitive action.")
                st.rerun()

            elif not full_response:
                st.error("⚠️ The agent returned an empty response.")

            else:
                clean_text = parse_response(full_response)
                message_placeholder.markdown(clean_text)
                st.session_state.messages.append({"role": "assistant", "content": clean_text})

        except Exception as e:
            logger.error(f"Execution Error: {e}", exc_info=True)
            st.error("🚨 An unexpected error occurred.")

try:
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    try:
        snapshot = graph.get_state(config)
    except Exception:
        snapshot = None

    if snapshot and snapshot.next and "tools" in snapshot.next:
        last_message = snapshot.values["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            sensitive_tools = [t for t in last_message.tool_calls if t["name"].startswith("action_")]

            if sensitive_tools:
                st.warning("⚠️ **APPROVAL REQUIRED**")

                for tool in sensitive_tools:
                    with st.expander(f"Checking Action: {tool['name']}", expanded=True):
                        st.json(tool['args'])

                col1, col2 = st.columns(2)

                if col1.button("✅ Approve Action"):
                    with st.spinner("Executing Action..."):
                        async def resume_sensitive():
                            last_msg = ""
                            async for event in graph.astream(None, config, stream_mode="values"):
                                if "messages" in event:
                                    last_msg = event["messages"][-1]
                            return last_msg.content if last_msg else ""


                        raw_result = run_async(resume_sensitive())
                        clean_result = parse_response(raw_result)

                        st.session_state.messages.append({"role": "assistant", "content": clean_result})
                        st.rerun()

                if col2.button("❌ Deny"):
                    st.error("Action Denied.")
                    st.stop()

except Exception as e:
    logger.error(f"State Check Failed: {e}", exc_info=True)
