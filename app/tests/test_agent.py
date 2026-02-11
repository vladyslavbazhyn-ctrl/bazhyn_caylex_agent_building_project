import pytest
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from langgraph.checkpoint.memory import MemorySaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.agent import (
    load_mcp_tools,
    build_graph,
    policy_lookup,
    get_current_date,
    summarize_case
)


# --- 1. TEST LOCAL TOOLS ---

def test_policy_lookup_found():
    """Test that policy lookup finds keywords."""
    result = policy_lookup.invoke({"query": "return policy"})
    assert "30 days" in result
    assert "VIP" in result


def test_policy_lookup_not_found():
    """Test fallback for unknown policies."""
    result = policy_lookup.invoke({"query": "parking policy"})
    assert "No specific policy found" in result


def test_get_current_date():
    """Test that date tool returns a string in YYYY-MM-DD format."""
    result = get_current_date.invoke({})
    assert len(result) == 10
    assert result.count("-") == 2


def test_summarize_case():
    """Test the summarization formatting."""
    result = summarize_case.invoke({
        "key_findings": ["Found Order 123", "Item Damaged"],
        "next_steps": "Issue Refund"
    })
    assert "CASE SUMMARY" in result
    assert "Found Order 123; Item Damaged" in result
    assert "Issue Refund" in result


# --- 2. TEST TOOL LOADING (MOCKED) ---

@pytest.mark.asyncio
async def test_load_mcp_tools():
    """
    Test that load_mcp_tools correctly combines:
    1. Remote tools (mocked)
    2. Local tools (policy, date, summary)
    """
    with patch("app.agents.agent.MultiServerMCPClient") as MockClient:
        mock_instance = MockClient.return_value

        mock_remote_tool = MagicMock()
        mock_remote_tool.name = "remote_tool_1"
        mock_instance.get_tools = AsyncMock(return_value=[mock_remote_tool])

        tools, client = await load_mcp_tools()

        assert client == mock_instance
        assert len(tools) == 4
        assert tools[0].name == "remote_tool_1"


# --- 3. TEST GRAPH CONSTRUCTION ---

def test_build_graph():
    """Test that the graph compiles and binds tools to the LLM."""
    mock_tools = [policy_lookup]

    real_checkpointer = MemorySaver()

    with patch("agents.agent.ChatGroq") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.bind_tools.return_value = mock_llm_instance

        graph = build_graph(mock_tools, real_checkpointer)

        assert graph is not None
        assert hasattr(graph, "stream") or hasattr(graph, "astream")
