import logging
import sys
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("COMMS_SERVER")

mcp = FastMCP("JewelryComms")


@mcp.tool()
def action_send_email_to_customer(email: str, subject: str, body: str) -> str:
    """[SIDE EFFECT] Sends an email to the customer. Requires confirmation."""
    logger.info(f"Sending email to {email} with subject: {subject}")
    return f"SUCCESS: Email sent to {email}. Subject: '{subject}'"


@mcp.tool()
def action_add_internal_note(customer_id: str, note: str) -> str:
    """[SIDE EFFECT] Log a note to the customer's permanent record."""
    logger.info(f"Adding note to customer {customer_id}: {note}")
    return f"SUCCESS: Note added to Customer {customer_id}: '{note}'"


if __name__ == "__main__":
    mcp.run()
