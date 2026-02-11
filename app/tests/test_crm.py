import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp_servers.server_crm import get_customer_profile


def test_get_customer_exact_vip():
    """Test finding a specific VIP customer."""
    result = get_customer_profile("Diamond")

    assert "CUST_001" in result
    assert "Alice Diamond" in result
    assert "VIP" in result


def test_get_customer_exact_regular():
    """Test finding a regular customer."""
    result = get_customer_profile("Bob")

    assert "CUST_002" in result
    assert "Regular" in result


def test_get_customer_ambiguous():
    """CRITICAL: Test that searching 'Alice' returns an ambiguity error."""
    result = get_customer_profile("Alice")

    assert "ERROR: AMBIGUOUS_MATCH" in result
    assert "Alice Diamond" in result
    assert "Alice Silver" in result


def test_get_customer_not_found():
    """Test searching for a non-existent user."""
    result = get_customer_profile("Zorro")
    assert "Customer not found" in result
