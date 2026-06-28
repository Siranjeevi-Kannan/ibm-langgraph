# AI-Powered Customer Support Automation System

Built with LangGraph for IBM Agentic AI course — Assignment 2

---

## Project Structure
```
customer_support_system/
│
├── documents/
│   ├── company_policy.txt
│   ├── pricing_guide.txt
│   ├── technical_manual.txt
│   └── faq.txt
├── schema/
│   └── schema.sql
├── main.py
├── rag.py
├── memory_store.py
├── memory.db
├── workflow.png
├── requirements.txt
└── README.md
```
---

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/) installed and running locally

---

## Setup

### 1. Pull the LLM

```bash
ollama pull qwen2.5:3b
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Project

### Demo mode — runs all 5 sample queries

```bash
python main.py --demo
```

### Interactive mode — chat with the system

```bash
python main.py --interactive
```
```
When prompted:

Enter your customer ID: cust_001
Enter your name: Raj
You: What are the pricing plans?
You: What was my previous support issue?
You: exit
```
### Skip human approval (auto-approve all requests)

```bash
python main.py --demo --no-hitl
```

### Run demo and interactive together

```bash
python main.py --demo --interactive
```

---

## Demo Queries (Task 10)

| # | Query | Expected Route |
|---|-------|----------------|
| Q1 | What are the pricing plans available for your software? | Sales Agent |
| Q2 | I forgot my account password. | Account Agent |
| Q3 | My application crashes whenever I upload a file. | Technical Agent |
| Q4 | I need a refund for my annual subscription. | Billing Agent → Human Approval |
| Q5 | What was my previous support issue? | Memory Recall |

---

## Human-in-the-Loop (Query 4)
```
When Query 4 runs, the system will pause and display the draft response, then prompt:

Options: approve / reject / modify
Decision:
```
Type one of the following and press Enter:

| Input | Action |
|-------|--------|
| `approve` | Sends the draft response to the customer |
| `reject` | Prompts for a rejection reason, sends rejection message |
| `modify` | Prompts you to type a new response manually |

---

## How It Works

| Component | Description |
|-----------|-------------|
| `classify_intent` | LLM classifies the query into sales, technical, billing, account, or memory |
| `route_intent` | Routes to the correct agent based on intent |
| `*_agent` | Specialized agents for each department |
| `fetch_rag_context` | Retrieves relevant info from the knowledge base |
| `human_approval` | Pauses for supervisor review on high-risk requests |
| `supervisor_agent` | Polishes the draft before sending the final response |
| `memory_store.py` | Saves and retrieves interaction history from SQLite |
| `rag.py` | Keyword-based retrieval over company documents |

---

## SQLite Memory

All interactions are saved to `memory.db` automatically after each query. This allows Query 5 to recall what Alice asked in Query 1.

To reset the database before a fresh run:

```bash
sqlite3 memory.db < schema.sql
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `langgraph` | Graph orchestration framework |
| `langgraph-checkpoint-sqlite` | SQLite checkpointing for graph state |
| `langchain-core` | Base LangChain interfaces |
| `langchain-ollama` | ChatOllama wrapper for local LLM |
| `rich` | Formatted terminal output |

