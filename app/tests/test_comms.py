import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp_servers.server_comms import action_send_email_to_customer, action_add_internal_note


def test_send_email():
    """Test that email tool returns the correct success message."""
    result = action_send_email_to_customer("test@example.com", "Hello", "Body content")
    assert "SUCCESS" in result
    assert "test@example.com" in result
    assert "Hello" in result


def test_add_internal_note():
    """Test that note tool returns the correct success message."""
    result = action_add_internal_note("CUST_123", "Customer is happy")
    assert "SUCCESS" in result
    assert "CUST_123" in result
    assert "Customer is happy" in result
