"""ABOUTME: DuckDB query functions for the Streamlit UI.
ABOUTME: Provides type/move search and data retrieval helpers."""

from pathlib import Path

import duckdb
import polars as pl

from unbounddb.build.database import get_connection
from unbounddb.build.normalize import slugify
from unbounddb.settings import settings


def _get_conn(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get database connection with fallback to settings."""
    if db_path is None:
        db_path = settings.db_path
    return get_connection(db_path)


def get_available_types(db_path: Path | None = None) -> list[str]:
    """Get list of unique Pokemon types from the database.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of type names.
    """
    conn = _get_conn(db_path)

    # Try to find a type column in pokemon table
    try:
        columns = conn.execute("DESCRIBE pokemon").fetchall()
        col_names = [c[0].lower() for c in columns]

        # Look for type columns
        type_cols = [c for c in col_names if "type" in c.lower()]

        if not type_cols:
            conn.close()
            return []

        # Get unique values from first type column
        type_col = type_cols[0]
        # Column names come from schema introspection, not user input
        result = conn.execute(
            f"SELECT DISTINCT {type_col} FROM pokemon WHERE {type_col} IS NOT NULL ORDER BY 1"  # noqa: S608
        ).fetchall()
        conn.close()

        return [r[0] for r in result if r[0]]
    except Exception:
        conn.close()
        return []


def get_available_moves(db_path: Path | None = None) -> list[str]:
    """Get list of unique move names from the database.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of move names.
    """
    conn = _get_conn(db_path)

    try:
        columns = conn.execute("DESCRIBE moves").fetchall()
        col_names = [c[0].lower() for c in columns]

        # Look for name column
        name_candidates = ["name", "move", "move_name"]
        name_col = None
        for candidate in name_candidates:
            if candidate in col_names:
                name_col = candidate
                break

        if name_col is None:
            conn.close()
            return []

        # Column names come from schema introspection, not user input
        result = conn.execute(
            f"SELECT DISTINCT {name_col} FROM moves WHERE {name_col} IS NOT NULL ORDER BY 1"  # noqa: S608
        ).fetchall()
        conn.close()

        return [r[0] for r in result if r[0]]
    except Exception:
        conn.close()
        return []


def search_pokemon_by_type_and_move(
    pokemon_type: str | None = None,
    move_name: str | None = None,
    db_path: Path | None = None,
) -> pl.DataFrame:
    """Search for Pokemon matching type and/or move criteria.

    Args:
        pokemon_type: Type to filter by (optional).
        move_name: Move the Pokemon must learn (optional).
        db_path: Optional path to database.

    Returns:
        DataFrame with matching Pokemon.
    """
    conn = _get_conn(db_path)

    try:
        # Get pokemon table columns to find type column
        pokemon_cols = conn.execute("DESCRIBE pokemon").fetchall()
        pokemon_col_names = [c[0] for c in pokemon_cols]
        type_cols = [c for c in pokemon_col_names if "type" in c.lower()]

        # Build query dynamically based on available tables and filters
        tables_available = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]

        # Start with base pokemon select
        # Column names come from schema introspection, not user input
        select_cols = ", ".join([f"p.{c}" for c in pokemon_col_names])
        query = f"SELECT DISTINCT {select_cols} FROM pokemon p"  # noqa: S608
        conditions: list[str] = []
        params: list[str] = []

        # Add pokemon_moves join if filtering by move
        if move_name and "pokemon_moves" in tables_available:
            query += " JOIN pokemon_moves pm ON p.pokemon_key = pm.pokemon_key"
            conditions.append("pm.move_key = ?")
            params.append(slugify(move_name))

        # Add type filter
        if pokemon_type and type_cols:
            type_col = type_cols[0]
            conditions.append(f"p.{type_col} = ?")
            params.append(pokemon_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Order by BST if available, otherwise by name
        bst_cols = [c for c in pokemon_col_names if "bst" in c.lower()]
        if bst_cols:
            query += f" ORDER BY p.{bst_cols[0]} DESC"
        else:
            name_cols = [c for c in pokemon_col_names if "name" in c.lower()]
            if name_cols:
                query += f" ORDER BY p.{name_cols[0]}"

        result = conn.execute(query, params).pl()
        conn.close()
        return result

    except Exception as e:
        conn.close()
        raise e


def get_table_preview(table_name: str, limit: int | None = 100, db_path: Path | None = None) -> pl.DataFrame:
    """Get a preview of a table's contents.

    Args:
        table_name: Name of the table to preview.
        limit: Maximum rows to return. None for all rows.
        db_path: Optional path to database.

    Returns:
        DataFrame with table contents.
    """
    conn = _get_conn(db_path)

    try:
        # Table name comes from get_table_list() which queries the schema
        if limit is None:
            result = conn.execute(f"SELECT * FROM {table_name}").pl()  # noqa: S608
        else:
            result = conn.execute(f"SELECT * FROM {table_name} LIMIT ?", [limit]).pl()  # noqa: S608
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e


def get_table_list(db_path: Path | None = None) -> list[str]:
    """Get list of available tables in the database.

    Args:
        db_path: Optional path to database.

    Returns:
        List of table names.
    """
    conn = _get_conn(db_path)

    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        conn.close()
        return [t[0] for t in tables]
    except Exception:
        conn.close()
        return []


def get_difficulties(db_path: Path | None = None) -> list[str]:
    """Get list of unique difficulty levels from trainers table.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of difficulty levels (excluding None).
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT DISTINCT difficulty FROM trainers WHERE difficulty IS NOT NULL ORDER BY difficulty"
        ).fetchall()
        conn.close()
        return [r[0] for r in result]
    except Exception:
        conn.close()
        return []


def get_trainers_by_difficulty(difficulty: str | None = None, db_path: Path | None = None) -> list[tuple[int, str]]:
    """Get list of (trainer_id, name) tuples, optionally filtered by difficulty.

    Args:
        difficulty: Optional difficulty level to filter by.
        db_path: Optional path to database.

    Returns:
        List of (trainer_id, name) tuples sorted by name.
    """
    conn = _get_conn(db_path)

    try:
        if difficulty is None:
            result = conn.execute("SELECT trainer_id, name FROM trainers ORDER BY name").fetchall()
        else:
            result = conn.execute(
                "SELECT trainer_id, name FROM trainers WHERE difficulty = ? ORDER BY name",
                [difficulty],
            ).fetchall()
        conn.close()
        return [(r[0], r[1]) for r in result]
    except Exception:
        conn.close()
        return []


def get_trainer_by_id(trainer_id: int, db_path: Path | None = None) -> dict[str, str | None] | None:
    """Get trainer details by ID.

    Args:
        trainer_id: ID of the trainer.
        db_path: Optional path to database.

    Returns:
        Dictionary with trainer details or None if not found.
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT trainer_id, name, difficulty FROM trainers WHERE trainer_id = ?",
            [trainer_id],
        ).fetchone()
        conn.close()
        if result:
            return {
                "trainer_id": result[0],
                "name": result[1],
                "difficulty": result[2],
            }
        return None
    except Exception:
        conn.close()
        return None


def get_trainer_team_with_moves(trainer_id: int, db_path: Path | None = None) -> pl.DataFrame:
    """Get a trainer's full team with Pokemon types and move details.

    Joins: trainers -> trainer_pokemon -> pokemon (for types)
           trainer_pokemon -> trainer_pokemon_moves -> moves (for move types)

    Args:
        trainer_id: ID of the trainer.
        db_path: Optional path to database.

    Returns:
        DataFrame with trainer's team and move information.
    """
    conn = _get_conn(db_path)

    query = """
        SELECT
            tp.pokemon_key,
            tp.slot,
            p.type1 AS pokemon_type1,
            p.type2 AS pokemon_type2,
            tpm.move_key,
            m.name AS move_name,
            m.type AS move_type,
            m.category AS move_category
        FROM trainer_pokemon tp
        JOIN pokemon p ON tp.pokemon_key = p.pokemon_key
        JOIN trainer_pokemon_moves tpm ON tp.id = tpm.trainer_pokemon_id
        JOIN moves m ON tpm.move_key = m.move_key
        WHERE tp.trainer_id = ?
        ORDER BY tp.slot, tpm.slot
    """

    try:
        result = conn.execute(query, [trainer_id]).pl()
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e


def get_all_location_names(db_path: Path | None = None) -> list[str]:
    """Get sorted list of unique location names from the locations table.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of unique location names.
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT DISTINCT location_name FROM locations WHERE location_name IS NOT NULL ORDER BY location_name"
        ).fetchall()
        conn.close()
        return [r[0] for r in result if r[0]]
    except Exception:
        conn.close()
        return []


def get_all_pokemon_names_from_locations(db_path: Path | None = None) -> list[str]:
    """Get sorted list of unique Pokemon names from the locations table.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of unique Pokemon names.
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT DISTINCT pokemon FROM locations WHERE pokemon IS NOT NULL ORDER BY pokemon"
        ).fetchall()
        conn.close()
        return [r[0] for r in result if r[0]]
    except Exception:
        conn.close()
        return []


def search_pokemon_locations(pokemon_name: str, db_path: Path | None = None) -> pl.DataFrame:
    """Search for all locations where a Pokemon can be caught.

    Args:
        pokemon_name: The Pokemon name to search for (case-insensitive).
        db_path: Optional path to database.

    Returns:
        DataFrame with columns: location_name, encounter_method, encounter_notes, requirement.
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            """
            SELECT location_name, encounter_method, encounter_notes, requirement
            FROM locations
            WHERE LOWER(pokemon) = LOWER(?)
            ORDER BY location_name, encounter_method
            """,
            [pokemon_name],
        ).pl()
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e
