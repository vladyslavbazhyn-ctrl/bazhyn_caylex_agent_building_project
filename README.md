# 💎 JewelryOps AI Agent
A Tool-Using, Human-in-the-Loop AI Agent for Vertical SaaS

This repository contains a fully functional AI agent designed for JewelryOps, a SaaS platform for jewelry retailers. 
Unlike a simple chatbot or RAG chain, this is a stateful Agent built with LangGraph that runs in a cognitive loop (Observe -> Decide -> Act), manages its own memory, and orchestrates tools across three distinct simulated systems.

# 🏗️ Architecture
This project implements a Model Context Protocol (MCP) architecture to decouple the Agent's "Brain" from its "Tools".

## The Core Components
### The Brain:

Built on LangGraph.

Uses Google Gemini 2.5 Flash (via Google AI Studio) for decision-making.
Maintains conversation state using MemorySaver and add_messages reducer.

### The Frontend:

Streamlit interface for user interaction.

Manages the Async Event Loop to handle asynchronous tool execution alongside the synchronous UI.
Implements Human-in-the-Loop interrupts for sensitive actions.

### The Tool Layer (MCP Servers):

CRM Server (server_crm.py): Manages customer data and handles ambiguity (e.g., duplicate names).
OMS Server (server_oms.py): Handles Orders & Inventory. Includes "Side Effect" tools like Refunds.
Comms Server (server_comms.py): Handles simulated emails and internal notes.

# 🧠 How the agent manages context and tool selection
## This agent uses a Dynamic Reasoning Loop:

### 1. Context Management:

- The agent uses MemorySaver to persist the chat history.
- It remembers entities found in previous turns (e.g., if you find "Alice's ID" in turn 1, you can say "Check her orders" in turn 2).

### 2. Tool Selection Strategy:

- Dynamic Sequencing: The System Prompt instructs the agent to form its own plan based on the user's goal. For example, if a Return is blocked by policy, the agent autonomously pivots to check the Warranty policy.
- Parallel Execution: To improve efficiency, the agent is instructed to call multiple independent tools (e.g., get_order_details + check_inventory) in a single turn.

### 3. Ambiguity Handling:

- If the CRM tool returns multiple matches (e.g., two "Alices"), the tool returns a specific AMBIGUOUS_MATCH error signal.
- The Agent is programmed to halt execution and ask the user for clarification, preventing hallucinations.

# 🚀 Features
✅ Runs in a cyclic graph.

✅ Remembers previous turns.

✅ 3 MCP Toolsets.

✅ Custom Logic Tools.

✅ Strictly enforces Human Confirmation before executing sensitive tools.

✅ Clarifying questions to ask for help when data is ambiguous.

# 🛠️ Setup & Installation
This project uses uv for extremely fast dependency management.

## 1. Prerequisites
- Python 3.10+
- uv installed
- you have .env file created according to .env.example
- Google AI Studio API Key

## 2. Installation
### Clone the repo
### Install dependencies:
- uv sync
#### OR manually
- uv add langchain langgraph langchain-google-genai streamlit mcp langchain-mcp-adapters python-dotenv

## 3. Environment Configuration
- Create a .env file in the root directory: GCP_API_KEY=AIzaSy...

# ▶️ How to Run it
Because the MCP servers are launched as subprocesses by the Agent, you only need to run the Streamlit app.

uv run streamlit run app.py
