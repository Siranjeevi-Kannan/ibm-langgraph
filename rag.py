import os
from typing import List

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")

DOCUMENT_FILES = {
    "Company Policy":   "company_policy.txt",
    "Pricing Guide":    "pricing_guide.txt",
    "Technical Manual": "technical_manual.txt",
    "FAQ":              "faq.txt",
}

INTENT_KEYWORDS = {
    "sales":     ["pricing", "plan", "cost", "price", "subscribe", "subscription",
                  "feature", "trial", "upgrade", "downgrade", "discount", "monthly", "annual"],
    "technical": ["crash", "error", "bug", "fix", "install", "login", "password",
                  "upload", "configuration", "not working", "broken", "slow", "err_"],
    "billing":   ["refund", "invoice", "payment", "charge", "cancel", "billing",
                  "receipt", "overcharge", "money back", "compensation"],
    "account":   ["account", "profile", "reset", "activate", "deactivate", "close",
                  "delete", "update", "username", "email change"],
}


def _load_chunks() -> List[tuple]:
    chunks = []
    for doc_name, filename in DOCUMENT_FILES.items():
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        for line in lines:
            if len(line) > 30:
                chunks.append((doc_name, line))
    return chunks


DOCUMENT_CHUNKS = _load_chunks()


def retrieve_context(query: str, top_k: int = 5) -> str:
    query_lower = query.lower()
    query_words = set(query_lower.split())
    scored_chunks: List[tuple] = []

    for source, chunk in DOCUMENT_CHUNKS:
        chunk_lower = chunk.lower()
        score = 0
        chunk_words = set(chunk_lower.split())
        overlap = len(query_words & chunk_words)
        score += overlap * 2

        for keyword in query_words:
            if keyword in chunk_lower:
                score += 1

        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                if any(kw in chunk_lower for kw in keywords):
                    score += 3

        if score > 0:
            scored_chunks.append((score, source, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:top_k]

    if not top_chunks:
        return "No specific documentation found for this query."

    return "\n\n".join(f"[{source}] {chunk}" for score, source, chunk in top_chunks)
