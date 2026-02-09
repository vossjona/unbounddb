# ABOUTME: SQLite operations for user profile storage.
# ABOUTME: Provides CRUD functions for profiles with progression step and difficulty settings.

import sqlite3
from pathlib import Path
from typing import Any

from unbounddb.settings import settings

# Schema for the profiles table
_PROFILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    name VARCHAR PRIMARY KEY,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    difficulty VARCHAR,
    progression_step INTEGER NOT NULL DEFAULT 0,
    rod_level VARCHAR NOT NULL DEFAULT 'None'
)
"""


def _get_user_db_path() -> Path:
    """Get path to user database, allows tests to override via settings."""
    return settings.user_db_path


def get_user_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a writable connection to the user data database.

    Creates the database and schema if they don't exist.

    Args:
        db_path: Optional path to database. Defaults to settings.user_db_path.

    Returns:
        SQLite connection (writable).
    """
    if db_path is None:
        db_path = _get_user_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the profiles table if it doesn't exist, migrating from old schema if needed.

    Args:
        conn: Active SQLite connection.
    """
    conn.execute(_PROFILES_SCHEMA)
    conn.commit()

    # Migrate: if old schema detected (has has_surf but no progression_step), recreate
    columns = conn.execute("PRAGMA table_info('profiles')").fetchall()
    col_names = {row[1] for row in columns}
    if "progression_step" not in col_names:
        conn.execute("DROP TABLE profiles")
        conn.execute(_PROFILES_SCHEMA)
        conn.commit()


def list_profiles(db_path: Path | None = None) -> list[str]:
    """Get all profile names from the database.

    Args:
        db_path: Optional path to database.

    Returns:
        List of profile names, sorted alphabetically.
    """
    conn = get_user_connection(db_path)
    try:
        result = conn.execute("SELECT name FROM profiles ORDER BY name").fetchall()
        return [row[0] for row in result]
    finally:
        conn.close()


def get_profile(name: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """Get a single profile's data by name.

    Args:
        name: Profile name to retrieve.
        db_path: Optional path to database.

    Returns:
        Dictionary with profile fields, or None if not found.
    """
    conn = get_user_connection(db_path)
    try:
        result = conn.execute(
            """
            SELECT name, active, difficulty, progression_step, rod_level
            FROM profiles WHERE name = ?
            """,
            [name],
        ).fetchone()

        if result is None:
            return None

        return {
            "name": result[0],
            "active": bool(result[1]),
            "difficulty": result[2],
            "progression_step": result[3],
            "rod_level": result[4],
        }
    finally:
        conn.close()


def create_profile(name: str, db_path: Path | None = None) -> bool:
    """Create a new profile with default settings.

    Args:
        name: Profile name to create.
        db_path: Optional path to database.

    Returns:
        True if created successfully, False if name already exists.
    """
    conn = get_user_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO profiles (name, active, progression_step, rod_level)
            VALUES (?, 0, 0, 'None')
            """,
            [name],
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_profile(name: str, db_path: Path | None = None, **fields: object) -> bool:
    """Update specific fields of a profile.

    Args:
        name: Profile name to update.
        db_path: Optional path to database.
        **fields: Field names and values to update. Valid fields:
            difficulty, progression_step, rod_level

    Returns:
        True if profile was found and updated, False otherwise.
    """
    if not fields:
        return False

    valid_fields = {
        "difficulty",
        "progression_step",
        "rod_level",
    }

    # Filter to only valid fields
    updates = {k: v for k, v in fields.items() if k in valid_fields}
    if not updates:
        return False

    conn = get_user_connection(db_path)
    try:
        # Build SET clause - field names are from valid_fields set, not user input
        set_parts = [f"{field} = ?" for field in updates]
        set_clause = ", ".join(set_parts)
        values = [*list(updates.values()), name]

        cursor = conn.execute(
            f"UPDATE profiles SET {set_clause} WHERE name = ?",  # noqa: S608
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_profile(name: str, db_path: Path | None = None) -> bool:
    """Delete a profile by name.

    Args:
        name: Profile name to delete.
        db_path: Optional path to database.

    Returns:
        True if deleted, False if not found.
    """
    conn = get_user_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM profiles WHERE name = ?", [name])
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_active_profile(db_path: Path | None = None) -> str | None:
    """Get the name of the currently active profile.

    Args:
        db_path: Optional path to database.

    Returns:
        Name of the active profile, or None if no profile is active.
    """
    conn = get_user_connection(db_path)
    try:
        result = conn.execute("SELECT name FROM profiles WHERE active = 1").fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def set_active_profile(name: str | None, db_path: Path | None = None) -> None:
    """Set the active profile.

    Clears active status from all profiles, then sets the named profile as active.

    Args:
        name: Profile name to set as active, or None to deactivate all.
        db_path: Optional path to database.
    """
    conn = get_user_connection(db_path)
    try:
        # Clear all active flags first
        conn.execute("UPDATE profiles SET active = 0")

        # Set the new active profile
        if name is not None:
            conn.execute("UPDATE profiles SET active = 1 WHERE name = ?", [name])

        conn.commit()
    finally:
        conn.close()


def profile_exists(name: str, db_path: Path | None = None) -> bool:
    """Check if a profile exists.

    Args:
        name: Profile name to check.
        db_path: Optional path to database.

    Returns:
        True if profile exists, False otherwise.
    """
    conn = get_user_connection(db_path)
    try:
        result = conn.execute("SELECT 1 FROM profiles WHERE name = ?", [name]).fetchone()
        return result is not None
    finally:
        conn.close()


def get_profile_count(db_path: Path | None = None) -> int:
    """Get the number of profiles in the database.

    Args:
        db_path: Optional path to database.

    Returns:
        Number of profiles.
    """
    conn = get_user_connection(db_path)
    try:
        result = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()
        return result[0] if result else 0
    finally:
        conn.close()
