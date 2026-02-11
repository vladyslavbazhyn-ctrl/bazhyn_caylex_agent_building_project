import sqlite3
from sqlite3 import Connection
import logging
import sys
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("CRM_SERVER")


def init_db() -> Connection:
    """Initialize in-memory database with mock customer data."""
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = connection.cursor()

    # Customers table
    cursor.execute("CREATE TABLE customers (id TEXT, name TEXT, email TEXT, vip_status BOOL)")
    cursor.execute("INSERT INTO customers VALUES ('CUST_001', 'Alice Diamond', 'alice.d@example.com', 1)")
    cursor.execute("INSERT INTO customers VALUES ('CUST_999', 'Alice Silver', 'alice.s@example.com', 0)")
    cursor.execute("INSERT INTO customers VALUES ('CUST_002', 'Bob Gold', 'bob@example.com', 0)")

    connection.commit()
    return connection


conn = init_db()
mcp = FastMCP("JewelryCRM")


@mcp.tool()
def get_customer_profile(name: str) -> str:
    """Look up a customer's email, ID, and VIP status by their name."""
    logger.info(f"Searching for customer name LIKE '%{name}%'")

    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, vip_status FROM customers WHERE name LIKE ?", (f"%{name}%",))
    rows = cursor.fetchall()

    if not rows:
        logger.warning(f"No customer found for query: {name}")
        return "Customer not found."

    if len(rows) > 1:
        names = [f"{r[1]} (ID: {r[0]})" for r in rows]
        logger.warning(f"Ambiguous match for '{name}'. Found: {names}")
        return (
            f"ERROR: AMBIGUOUS_MATCH. Multiple customers found: {', '.join(names)}. "
            f"You MUST ask the user to clarify which one they mean."
        )

    r = rows[0]
    logger.info(f"Found customer: {r[1]} ({r[0]})")
    return f"ID: {r[0]} | Name: {r[1]} | Email: {r[2]} | Status: {'VIP' if r[3] else 'Regular'}"


if __name__ == "__main__":
    mcp.run()
