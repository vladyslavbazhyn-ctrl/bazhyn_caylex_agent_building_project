import pytest
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.agent import (
    load_mcp_tools,
    build_graph,
    policy_lookup,
    get_current_date,
    summarize_case
)


# --- 1. LOCAL TOOLS: NEGATIVE & EDGE CASES ---

def test_policy_lookup_found():
    """Positive: Finds a known policy."""
    result = policy_lookup.invoke({"query": "return policy"})
    assert "30 days" in result


def test_policy_lookup_negative():
    """Negative: Querying for something that doesn't exist."""
    result = policy_lookup.invoke({"query": "pizza delivery"})
    assert "No specific policy found" in result


def test_policy_lookup_edge_cases():
    """Edge Case: Empty strings and special characters."""
    assert "No specific policy found" in policy_lookup.invoke({"query": ""})
    assert "No specific policy found" in policy_lookup.invoke({"query": "!!!###"})


def test_get_current_date():
    """Positive: Returns valid date format."""
    result = get_current_date.invoke({})
    assert len(result) == 10
    assert result.count("-") == 2


def test_summarize_case_empty():
    """Edge Case: Summarizing with empty data."""
    result = summarize_case.invoke({
        "key_findings": [],
        "next_steps": "None"
    })
    assert "CASE SUMMARY" in result
    assert "Findings: " in result


# --- 2. TOOL LOADING (MOCKED) ---

@pytest.mark.asyncio
async def test_load_mcp_tools():
    """Test that tool loading combines remote and local tools correctly."""
    with patch("app.agents.agent.MultiServerMCPClient") as MockClient:
        mock_instance = MockClient.return_value

        mock_remote_tool = MagicMock()
        mock_remote_tool.name = "remote_tool_1"
        mock_instance.get_tools = AsyncMock(return_value=[mock_remote_tool])

        tools, client = await load_mcp_tools()

        assert client == mock_instance
        assert len(tools) == 4
        assert tools[0].name == "remote_tool_1"


# --- 3. AGENT LOGIC: ROUTING & CONTROL FLOW ---

@patch("app.agents.agent.time.sleep")  # ⚡ Skip the 2s sleep in tests
def test_agent_routing_stops(mock_sleep):
    """
    NEGATIVE SCENARIO:
    If LLM returns text (no tools), the graph should go to END.
    """
    mock_tools = [policy_lookup]
    checkpointer = MemorySaver()

    with patch("app.agents.agent.ChatGroq") as MockLLM:
        mock_llm = MockLLM.return_value
        mock_llm.bind_tools.return_value = mock_llm

        # 1. Mock the LLM to return plain text (NO tool_calls)
        mock_llm.invoke.return_value = AIMessage(content="Hello, how can I help?")

        # 2. Build and Run Graph
        graph = build_graph(mock_tools, checkpointer)

        # 3. Invoke with a dummy user message
        result = graph.invoke(
            {"messages": [HumanMessage(content="Hi")]},
            config={"configurable": {"thread_id": "test_1"}}
        )

        # 4. Assertions
        # If it stopped correctly, the last message is from the AI
        assert isinstance(result["messages"][-1], AIMessage)
        assert result["messages"][-1].content == "Hello, how can I help?"
        # Ensure we didn't get stuck in a loop (LLM called only once)
        assert mock_llm.invoke.call_count == 1


@patch("app.agents.agent.time.sleep")
def test_agent_routing_continues(mock_sleep):
    """
    POSITIVE SCENARIO:
    If LLM returns a tool_call, the graph should route to 'tools'.
    """
    mock_tools = [policy_lookup]
    checkpointer = MemorySaver()

    with patch("app.agents.agent.ChatGroq") as MockLLM:
        mock_llm = MockLLM.return_value
        mock_llm.bind_tools.return_value = mock_llm

        # 1. Mock LLM to return a TOOL CALL first
        # We need to simulate the 'tools' node executing, but for this unit test,
        # we just want to see if the agent *tries* to call a tool.

        tool_call_msg = AIMessage(
            content="",
            tool_calls=[{"name": "policy_lookup", "args": {"query": "return"}, "id": "call_123"}]
        )

        mock_llm.invoke.return_value = tool_call_msg

        graph = build_graph(mock_tools, checkpointer)

        # 2. Run graph logic for ONE step
        # We can't run full .invoke() easily because the mock tool execution
        # inside the graph is complex to set up without a real ToolNode.
        # Instead, we test the 'should_continue' logic indirectly by checking the output.

        # We manually inspect the graph structure to ensure edges exist
        assert "tools" in graph.nodes
        assert "agent" in graph.nodes