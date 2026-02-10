# ABOUTME: Lightweight SQLite connection and query helpers for the app layer.
# ABOUTME: Avoids importing Polars/PyArrow so Streamlit Cloud stays under memory limits.

import sqlite3
from pathlib import Path
from typing import Any


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a connection to an existing database.

    Args:
        db_path: Path to the database file.

    Returns:
        SQLite connection.

    Raises:
        FileNotFoundError: If database doesn't exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    return sqlite3.connect(str(db_path), check_same_thread=False)


def fetchall_to_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    """Convert a SQLite cursor result to a list of dictionaries.

    Args:
        cursor: Executed SQLite cursor with results.

    Returns:
        List of dicts, one per row, with column names as keys.
    """
    if cursor.description is None:
        return []

    column_names = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    return [dict(zip(column_names, row, strict=True)) for row in rows]
