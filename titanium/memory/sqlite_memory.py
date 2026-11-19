import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from titanium.config import DB_PATH

class MemoryManager:
    """Lightweight persistent SQLite memory for Titanium (< 2MB RAM)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT
                )
            """)
            # Facts & User Preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TEXT NOT NULL
                )
            """)
            # Sessions & summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    summary TEXT
                )
            """)
            conn.commit()

    def add_message(self, role: str, content: str, model: str = "") -> None:
        """Add a single message to history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (timestamp, role, content, model) VALUES (?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(), role, content, model)
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Fetch the most recent turns."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def set_fact(self, key: str, value: str, category: str = "general") -> None:
        """Store or update a learned fact or preference."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO facts (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
            """, (key, value, category, datetime.datetime.now().isoformat()))
            conn.commit()

    def get_fact(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM facts WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    def get_all_facts(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM facts")
            return {r["key"]: r["value"] for r in cursor.fetchall()}

    def get_context_prompt(self) -> str:
        """Returns a concise summary of learned facts to inject into prompt."""
        facts = self.get_all_facts()
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts.items()]
        return "Learned User Preferences & Facts:\n" + "\n".join(lines)
