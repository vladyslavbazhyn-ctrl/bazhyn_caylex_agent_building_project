from mcp.server.fastmcp import FastMCP
import sqlite3


def init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()

    # Orders Table
    cursor.execute("CREATE TABLE orders (id TEXT, customer_id TEXT, date TEXT, status TEXT)")
    cursor.execute("INSERT INTO orders VALUES ('ORD_101', 'CUST_001', '2023-10-01', 'DELIVERED')")
    cursor.execute("INSERT INTO orders VALUES ('ORD_102', 'CUST_002', '2025-01-15', 'PROCESSING')")
    cursor.execute("INSERT INTO orders VALUES ('ORD_999', 'CUST_999', '2025-10-20', 'SHIPPED')")

    # Order Items Table
    cursor.execute("CREATE TABLE order_items (order_id TEXT, item TEXT, qty INT)")
    cursor.execute("INSERT INTO order_items VALUES ('ORD_101', 'Sapphire Necklace', 1)")
    cursor.execute("INSERT INTO order_items VALUES ('ORD_102', 'Gold Ring', 1)")
    cursor.execute("INSERT INTO order_items VALUES ('ORD_999', 'Gold Necklace', 2)")

    # Inventory Table
    cursor.execute("CREATE TABLE inventory (item TEXT, stock INT, location TEXT)")
    cursor.execute("INSERT INTO inventory VALUES ('Sapphire Necklace', 5, 'Vault A')")
    cursor.execute("INSERT INTO inventory VALUES ('Gold Ring', 12, 'Display Case')")

    conn.commit()
    return conn


conn = init_db()
mcp = FastMCP("JewelryOMS")


@mcp.tool()
def get_customer_orders(customer_id: str) -> str:
    """Returns a list of Order IDs and Dates for a customer. DOES NOT show items or status."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, date FROM orders WHERE customer_id = ?", (customer_id,))
    rows = cursor.fetchall()
    if not rows:
        return "No orders found."
    return "\n".join([f"Order ID: {r[0]} | Date: {r[1]}" for r in rows])


@mcp.tool()
def get_order_details(order_id: str) -> str:
    """Get the Status and Items for a specific Order ID."""
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    status_res = cursor.fetchone()
    if not status_res: return "Order ID not found."

    cursor.execute("SELECT item, qty FROM order_items WHERE order_id = ?", (order_id,))
    items_res = cursor.fetchall()

    items_str = ", ".join([f"{r[1]}x {r[0]}" for r in items_res])
    return f"Order {order_id}\nStatus: {status_res[0]}\nItems: {items_str}"


@mcp.tool()
def check_inventory(item_name: str) -> str:
    """Check system stock levels for an item."""
    cursor = conn.cursor()
    cursor.execute("SELECT stock, location FROM inventory WHERE item LIKE ?", (f"%{item_name}%",))
    res = cursor.fetchone()
    if res:
        return f"Item: {item_name} | System Stock: {res[0]} | Location: {res[1]}"
    return "Item not found in inventory."


@mcp.tool()
def action_process_refund(order_id: str, reason: str) -> str:
    """[SIDE EFFECT] Process a full refund. Use ONLY after policy check."""
    return f"SUCCESS: Refund processed for {order_id}. Reason: {reason}"


if __name__ == "__main__":
    mcp.run()
