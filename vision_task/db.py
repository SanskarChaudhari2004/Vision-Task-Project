"""Persistent storage layer for Vision Task.

This module uses SQLite to store tasks persistently between server restarts.
It exposes minimal helpers for initializing the database and reading/writing tasks.
"""

import os
import sqlite3
from datetime import datetime
import json
from typing import List, Optional

from .models import Task, SensitivityLevel, TaskStatus, User

def _get_db_path() -> str:
    """Return the SQLite database path.

    This reads the VISION_TASK_DB environment variable each time so that the
    database file can be changed at runtime (e.g., tests setting a temp file).
    """
    return os.environ.get("VISION_TASK_DB") or "vision_task.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the SQLite database file and required tables."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            sensitivity TEXT NOT NULL,
            created_by TEXT NOT NULL,
            assigned_to TEXT,
            department TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            priority INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            roles TEXT NOT NULL,
            department TEXT,
            can_view_high_sensitivity INTEGER NOT NULL,
            can_view_medium_sensitivity INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        sensitivity=SensitivityLevel(row["sensitivity"]),
        created_by=row["created_by"],
        assigned_to=row["assigned_to"],
        department=row["department"],
        status=TaskStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        priority=row["priority"],
    )


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        username=row["username"],
        password_hash=row["password_hash"],
        roles=json.loads(row["roles"]),
        department=row["department"],
        can_view_high_sensitivity=bool(row["can_view_high_sensitivity"]),
        can_view_medium_sensitivity=bool(row["can_view_medium_sensitivity"]),
    )


def list_tasks() -> List[Task]:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_task(r) for r in rows]


def list_users() -> List[User]:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_user(r) for r in rows]


def get_task_by_id(task_id: str) -> Optional[Task]:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_task(row) if row else None


def get_user(username: str) -> Optional[User]:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def insert_task(task: Task):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO tasks
        (id, title, description, sensitivity, created_by, assigned_to, department,
         status, created_at, updated_at, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task.id,
            task.title,
            task.description,
            task.sensitivity.value,
            task.created_by,
            task.assigned_to,
            task.department,
            task.status.value,
            task.created_at.isoformat(),
            task.updated_at.isoformat(),
            task.priority,
        ),
    )
    conn.commit()
    conn.close()


def insert_user(user: User):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO users
        (username, password_hash, roles, department, can_view_high_sensitivity, can_view_medium_sensitivity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user.username,
            user.password_hash,
            json.dumps(user.roles),
            user.department,
            1 if user.can_view_high_sensitivity else 0,
            1 if user.can_view_medium_sensitivity else 0,
        ),
    )
    conn.commit()
    conn.close()


def delete_task(task_id: str):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def delete_user(username: str):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = ?", (username,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0
