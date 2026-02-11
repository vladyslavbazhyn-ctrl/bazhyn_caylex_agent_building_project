import asyncio
import sys
import uuid
import logging
import streamlit as st


from typing import Coroutine, Any, TypeVar, Tuple
from agents.agent import load_mcp_tools, build_graph


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("APP_HELPERS")

T = TypeVar("T")


def parse_response(content: Any) -> str:
    """Parses JSON response from LLM into a clean string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(text_parts)
    return str(content)


def run_async(coroutine: Coroutine[Any, Any, T]) -> T:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coroutine)
            return future.result()
    else:
        return asyncio.run(coroutine)


def get_graph_and_client() -> Tuple[Any, Any]:
    async def _init() -> Tuple[Any, Any]:
        tools, client = await load_mcp_tools()
        graph = build_graph(tools, checkpointer=st.session_state.memory)
        return graph, client

    return run_async(_init())


def reset_memory() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    logger.info(f"♻️ Memory cleared. New ID: {st.session_state.thread_id}")
