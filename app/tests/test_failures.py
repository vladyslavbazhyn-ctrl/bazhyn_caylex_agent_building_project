import pytest
import sys
import os
from unittest.mock import patch
from langchain_core.messages import HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.agent import build_graph, policy_lookup
from langgraph.checkpoint.memory import MemorySaver


def test_llm_api_failure_propagates():
    """
    CRITICAL TEST: Verify that if Groq fails (e.g. Rate Limit),
    the error bubbles up so app.py can catch it in the UI.
    """
    mock_tools = [policy_lookup]
    checkpointer = MemorySaver()

    with patch("app.agents.agent.ChatGroq") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.bind_tools.return_value.invoke.side_effect = Exception("GROQ_API_500: Service Unavailable")

        graph = build_graph(mock_tools, checkpointer)

        with pytest.raises(Exception) as excinfo:
            graph.invoke(
                {"messages": [HumanMessage(content="Hi")]},
                config={"configurable": {"thread_id": "fail_test"}}
            )

        assert "GROQ_API_500" in str(excinfo.value)


def test_tool_execution_failure():
    """
    Verify behavior when input validation fails.
    """

    try:
        policy_lookup.invoke({"query": None})
    except Exception as e:
        error_msg = str(e).lower()
        assert "validation error" in error_msg
        assert "input should be a valid string" in error_msg
