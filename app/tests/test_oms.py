import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp_servers.server_oms import (
    get_customer_orders,
    get_order_details,
    check_inventory,
    action_process_refund
)


def test_get_customer_orders_found():
    """Test fetching orders for a known customer."""
    result = get_customer_orders("CUST_001")
    assert "ORD_101" in result
    assert "2023-10-01" in result


def test_get_customer_orders_empty():
    """Test fetching orders for a valid customer with no orders (or invalid ID)."""
    result = get_customer_orders("CUST_NON_EXISTENT")
    assert "No orders found" in result


def test_get_order_details_valid():
    """Test fetching details for a specific order."""
    result = get_order_details("ORD_101")
    assert "DELIVERED" in result
    assert "Sapphire Necklace" in result


def test_get_order_details_invalid():
    """Test fetching details for a missing order."""
    result = get_order_details("ORD_99999")
    assert "Order ID not found" in result


def test_check_inventory_found():
    """Test checking stock for an existing item."""
    result = check_inventory("Sapphire")
    assert "System Stock: 5" in result
    assert "Vault A" in result


def test_check_inventory_missing():
    """Test checking stock for a missing item."""
    result = check_inventory("Unobtainium")
    assert "Item not found" in result


def test_process_refund():
    """Test the refund action string format."""
    result = action_process_refund("ORD_101", "Damaged item")
    # ✅ FIX: The string must be exactly "SUCCESS: Refund processed"
    assert "SUCCESS: Refund processed" in result
    assert "ORD_101" in result
