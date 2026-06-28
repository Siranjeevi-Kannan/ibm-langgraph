import sqlite3
import os
from typing import TypedDict, Optional, Annotated

from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from rich.console import Console
from rich.panel import Panel

from rag import retrieve_context
from memory_store import save_interaction, get_history

console = Console()

llm = ChatOllama(model="qwen2.5:3b", temperature=0)

HIGH_RISK_KEYWORDS = [
    "refund", "cancel subscription", "cancellation",
    "close account", "compensation", "escalate", "manager",
]


class SupportState(TypedDict):
    messages: Annotated[list, add_messages]
    customer_id: str
    customer_name: Optional[str]
    query: str
    intent: str
    is_high_risk: bool
    rag_context: str
    approval_status: str
    human_notes: str
    draft_response: str
    final_response: str


def classify_intent(state: SupportState) -> SupportState:
    query = state["query"]

    memory_phrases = ["previous issue", "last issue", "what did i ask", "earlier query",
                      "previous problem", "my history", "what was my"]
    if any(phrase in query.lower() for phrase in memory_phrases):
        state["intent"] = "memory"
        console.print("[bold cyan]Intent: MEMORY RECALL[/bold cyan]")
        return state

    prompt = f"""You are a customer support intent classifier for ABC Technologies.

Classify the following customer query into EXACTLY ONE category.

Query: {query}

Categories:
- sales       : product information, subscription plans, pricing, features
- technical   : application errors, crashes, installation issues, login problems, configuration
- billing     : invoice requests, payment issues, refund requests, subscription cancellation
- account     : password reset, profile updates, account activation or deactivation, account closure

Rules:
- Reply with ONLY one word (lowercase): sales, technical, billing, or account
- No punctuation, no explanation

Category:"""

    result = llm.invoke(prompt)
    raw = result.content.strip().lower().split()[0]
    valid = {"sales", "technical", "billing", "account"}
    state["intent"] = raw if raw in valid else "sales"
    state["is_high_risk"] = any(kw in query.lower() for kw in HIGH_RISK_KEYWORDS)

    console.print(f"[bold cyan]Intent: {state['intent'].upper()}  |  High-risk: {state['is_high_risk']}[/bold cyan]")
    return state


def route_intent(state: SupportState) -> str:
    intent = state["intent"]
    routes = {
        "memory": "memory_recall",
        "sales": "sales_agent",
        "technical": "technical_agent",
        "billing": "billing_agent",
        "account": "account_agent",
    }
    return routes.get(intent, "sales_agent")


def fetch_rag_context(state: SupportState) -> SupportState:
    context = retrieve_context(state["query"])
    state["rag_context"] = context
    console.print(f"[dim]RAG context retrieved ({len(context)} chars)[/dim]")
    return state


def _base_agent_prompt(role: str, dept: str, state: SupportState) -> str:
    name = state.get("customer_name") or "Customer"
    history = get_history(state["customer_id"])
    rag = state.get("rag_context", "")
    return f"""You are the {role} specialist at ABC Technologies.

Customer name: {name}
Department: {dept}

--- RELEVANT KNOWLEDGE BASE ---
{rag if rag else "No specific documents retrieved."}

--- PREVIOUS INTERACTIONS ---
{history if history else "No previous interactions found."}

--- CUSTOMER QUERY ---
{state['query']}

Instructions:
- Address the customer by name if known
- Be professional, empathetic, and concise (3-5 sentences)
- Use information from the knowledge base where relevant
- If this is a refund/cancellation/high-risk request, acknowledge that it requires approval

Response:"""


def sales_agent(state: SupportState) -> SupportState:
    console.print("[bold green]→ Sales Agent responding[/bold green]")
    state = fetch_rag_context(state)
    result = llm.invoke(_base_agent_prompt("Sales Support", "Sales", state))
    state["draft_response"] = result.content.strip()
    state["approval_status"] = "not_required"
    return state


def technical_agent(state: SupportState) -> SupportState:
    console.print("[bold green]→ Technical Support Agent responding[/bold green]")
    state = fetch_rag_context(state)
    result = llm.invoke(_base_agent_prompt("Technical Support", "Technical Support", state))
    state["draft_response"] = result.content.strip()
    state["approval_status"] = "not_required"
    return state


def billing_agent(state: SupportState) -> SupportState:
    console.print("[bold green]→ Billing Agent responding[/bold green]")
    state = fetch_rag_context(state)
    result = llm.invoke(_base_agent_prompt("Billing Support", "Billing", state))
    state["draft_response"] = result.content.strip()
    state["approval_status"] = "pending" if state.get("is_high_risk") else "not_required"
    return state


def account_agent(state: SupportState) -> SupportState:
    console.print("[bold green]→ Account Agent responding[/bold green]")
    state = fetch_rag_context(state)
    result = llm.invoke(_base_agent_prompt("Account Management", "Account", state))
    state["draft_response"] = result.content.strip()
    state["approval_status"] = "pending" if state.get("is_high_risk") else "not_required"
    return state


def memory_recall(state: SupportState) -> SupportState:
    console.print("[bold yellow]→ Memory Recall[/bold yellow]")
    history = get_history(state["customer_id"], limit=10)
    if not history:
        state["draft_response"] = "I don't have any previous interactions on record for your account."
    else:
        prompt = f"""You are a customer support agent at ABC Technologies.

The customer is asking about their previous support interactions.

--- CONVERSATION HISTORY ---
{history}

--- CUSTOMER QUERY ---
{state['query']}

Summarize the relevant past interactions to answer the customer's question clearly and concisely.

Response:"""
        result = llm.invoke(prompt)
        state["draft_response"] = result.content.strip()

    state["intent"] = "memory"
    state["approval_status"] = "not_required"
    return state


def needs_approval(state: SupportState) -> str:
    if state.get("approval_status") == "pending":
        return "human_approval"
    return "supervisor_agent"


def human_approval(state: SupportState) -> SupportState:
    console.print("\n[bold red]⚠ HUMAN APPROVAL REQUIRED[/bold red]")
    console.print(Panel(state["draft_response"], title="Draft Response", border_style="yellow"))

    console.print("\n[yellow]Options: approve / reject / modify[/yellow]")
    decision = input("Decision: ").strip().lower()

    if decision == "approve":
        state["approval_status"] = "approved"
        state["human_notes"] = "Approved by supervisor."
    elif decision == "reject":
        state["approval_status"] = "rejected"
        notes = input("Rejection reason: ").strip()
        state["human_notes"] = notes
        state["draft_response"] = f"We regret that we cannot process this request at this time. {notes}"
    elif decision == "modify":
        new_response = input("Enter modified response: ").strip()
        state["draft_response"] = new_response
        state["approval_status"] = "approved"
        state["human_notes"] = "Modified and approved by supervisor."
    else:
        state["approval_status"] = "approved"
        state["human_notes"] = "Auto-approved."

    return state


def supervisor_agent(state: SupportState) -> SupportState:
    console.print("[bold blue]→ Supervisor reviewing response[/bold blue]")

    if state.get("approval_status") == "rejected":
        state["final_response"] = state["draft_response"]
        _save_and_append(state)
        return state

    prompt = f"""You are a senior customer support supervisor at ABC Technologies.

Review and improve the following draft response before it is sent to the customer.

Customer query: {state['query']}
Intent: {state['intent']}
Approval status: {state['approval_status']}
Supervisor notes: {state.get('human_notes', '')}

Draft response:
{state['draft_response']}

Instructions:
1. Fix grammar, spelling, and tone
2. Ensure it is professional and empathetic
3. Ensure it matches the approval status
4. Keep it concise (under 150 words)
5. Do NOT change factual content or approval decisions

Improved response:"""

    result = llm.invoke(prompt)
    state["final_response"] = result.content.strip()
    _save_and_append(state)
    return state


def _save_and_append(state: SupportState):
    save_interaction(
        customer_id=state["customer_id"],
        intent=state["intent"],
        query=state["query"],
        response=state["final_response"],
    )
    state["messages"].append(AIMessage(content=state["final_response"]))


def build_graph(db_path: str = "memory.db"):
    builder = StateGraph(SupportState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("sales_agent", sales_agent)
    builder.add_node("technical_agent", technical_agent)
    builder.add_node("billing_agent", billing_agent)
    builder.add_node("account_agent", account_agent)
    builder.add_node("memory_recall", memory_recall)
    builder.add_node("human_approval", human_approval)
    builder.add_node("supervisor_agent", supervisor_agent)

    builder.set_entry_point("classify_intent")

    builder.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "sales_agent": "sales_agent",
            "technical_agent": "technical_agent",
            "billing_agent": "billing_agent",
            "account_agent": "account_agent",
            "memory_recall": "memory_recall",
        },
    )

    for agent in ["sales_agent", "technical_agent", "billing_agent", "account_agent", "memory_recall"]:
        builder.add_conditional_edges(
            agent,
            needs_approval,
            {
                "human_approval": "human_approval",
                "supervisor_agent": "supervisor_agent",
            },
        )

    builder.add_edge("human_approval", "supervisor_agent")
    builder.set_finish_point("supervisor_agent")

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return builder.compile(checkpointer=memory)


DEMO_QUERIES = [
    {"id": "Q1", "customer_id": "cust_001", "customer_name": "Alice",
     "query": "What are the pricing plans available for your software?", "expected": "Sales"},
    {"id": "Q2", "customer_id": "cust_002", "customer_name": "Bob",
     "query": "I forgot my account password.", "expected": "Account"},
    {"id": "Q3", "customer_id": "cust_003", "customer_name": "Carol",
     "query": "My application crashes whenever I upload a file.", "expected": "Technical Support"},
    {"id": "Q4", "customer_id": "cust_004", "customer_name": "David",
     "query": "I need a refund for my annual subscription.", "expected": "Billing — requires human approval"},
    {"id": "Q5", "customer_id": "cust_001", "customer_name": "Alice",
     "query": "What was my previous support issue?", "expected": "Memory recall"},
]


def run_demo(graph, interactive_hitl: bool = True):
    console.print("\n[bold magenta]" + "="*60 + "[/bold magenta]")
    console.print("[bold magenta]  ABC Technologies — Customer Support System Demo[/bold magenta]")
    console.print("[bold magenta]" + "="*60 + "[/bold magenta]\n")

    for demo in DEMO_QUERIES:
        console.print(f"\n[bold white]{'='*60}[/bold white]")
        console.print(f"[bold white]{demo['id']}: {demo['query']}[/bold white]")
        console.print(f"[dim]Expected path: {demo['expected']}[/dim]")
        console.print(f"[bold white]{'='*60}[/bold white]\n")

        initial_state: SupportState = {
            "messages": [HumanMessage(content=demo["query"])],
            "customer_id": demo["customer_id"],
            "customer_name": demo["customer_name"],
            "query": demo["query"],
            "intent": "",
            "is_high_risk": False,
            "rag_context": "",
            "approval_status": "not_required",
            "human_notes": "",
            "draft_response": "",
            "final_response": "",
        }

        config = {"configurable": {"thread_id": demo["customer_id"] + "_" + demo["id"]}}
        result = graph.invoke(initial_state, config=config)

        console.print(Panel(
            result["final_response"],
            title=f"[bold green]Final Response — {demo['id']} ({result['intent'].upper()})[/bold green]",
            border_style="green",
        ))

        if result["approval_status"] in ("approved", "rejected"):
            color = "green" if result["approval_status"] == "approved" else "red"
            console.print(f"[{color}]Approval: {result['approval_status'].upper()}[/{color}]")
            if result["human_notes"]:
                console.print(f"[dim]Notes: {result['human_notes']}[/dim]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--no-hitl", action="store_true")
    args = parser.parse_args()

    graph = build_graph()

    if args.demo or not args.interactive:
        run_demo(graph, interactive_hitl=not args.no_hitl)

    if args.interactive:
        console.print("\n[bold magenta]=== Interactive Support Chat ===[/bold magenta]")
        customer_id = input("Enter your customer ID: ").strip() or "cust_interactive"
        customer_name = input("Enter your name: ").strip() or "Customer"

        while True:
            query = input("\nYou: ").strip()
            if query.lower() in ("quit", "exit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break

            initial_state: SupportState = {
                "messages": [HumanMessage(content=query)],
                "customer_id": customer_id,
                "customer_name": customer_name,
                "query": query,
                "intent": "",
                "is_high_risk": False,
                "rag_context": "",
                "approval_status": "not_required",
                "human_notes": "",
                "draft_response": "",
                "final_response": "",
            }
            config = {"configurable": {"thread_id": customer_id}}
            result = graph.invoke(initial_state, config=config)
            console.print(Panel(result["final_response"], title="[bold green]Support[/bold green]", border_style="green"))