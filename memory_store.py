import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("SUPPORT_DB", "memory.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT    NOT NULL,
            intent      TEXT    NOT NULL,
            query       TEXT    NOT NULL,
            response    TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_interaction(customer_id: str, intent: str, query: str, response: str) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO interactions (customer_id, intent, query, response, timestamp) VALUES (?, ?, ?, ?, ?)",
        (customer_id, intent, query, response, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(customer_id: str, limit: int = 5) -> str:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT intent, query, response, timestamp FROM interactions WHERE customer_id = ? ORDER BY id DESC LIMIT ?",
        (customer_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return ""

    rows = list(reversed(rows))
    parts = []
    for i, row in enumerate(rows, 1):
        parts.append(
            f"Interaction {i} [{row['timestamp'][:10]}] ({row['intent'].upper()}):\n"
            f"  Customer: {row['query']}\n"
            f"  Support : {row['response'][:200]}{'...' if len(row['response']) > 200 else ''}"
        )
    return "\n\n".join(parts)


def get_all_customers() -> list:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT customer_id FROM interactions ORDER BY customer_id")
    rows = cursor.fetchall()
    conn.close()
    return [row["customer_id"] for row in rows]


def clear_history(customer_id: str) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interactions WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()


init_db()