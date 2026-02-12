# ABOUTME: SQLite query functions for the Streamlit UI.
# ABOUTME: Provides type/move search and data retrieval helpers.

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st

from unbounddb.app.db import fetchall_to_dicts, get_connection
from unbounddb.build.normalize import slugify
from unbounddb.settings import settings

if TYPE_CHECKING:
    from unbounddb.app.location_filters import LocationFilterConfig
    from unbounddb.app.move_search_filters import MoveSearchFilters


@st.cache_resource
def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    """Get database connection with fallback to settings."""
    if db_path is None:
        db_path = settings.db_path
    return get_connection(db_path)


@st.cache_data
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
        columns = conn.execute("PRAGMA table_info('pokemon')").fetchall()
        col_names = [c[1].lower() for c in columns]

        # Look for type columns
        type_cols = [c for c in col_names if "type" in c.lower()]

        if not type_cols:
            return []

        # Get unique values from first type column
        type_col = type_cols[0]
        # Column names come from schema introspection, not user input
        result = conn.execute(
            f"SELECT DISTINCT {type_col} FROM pokemon WHERE {type_col} IS NOT NULL ORDER BY 1"  # noqa: S608
        ).fetchall()

        return [r[0] for r in result if r[0]]
    except Exception:
        return []


@st.cache_data
def get_available_moves(db_path: Path | None = None) -> list[str]:
    """Get list of unique move names from the database.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of move names.
    """
    conn = _get_conn(db_path)

    try:
        columns = conn.execute("PRAGMA table_info('moves')").fetchall()
        col_names = [c[1].lower() for c in columns]

        # Look for name column
        name_candidates = ["name", "move", "move_name"]
        name_col = None
        for candidate in name_candidates:
            if candidate in col_names:
                name_col = candidate
                break

        if name_col is None:
            return []

        # Column names come from schema introspection, not user input
        result = conn.execute(
            f"SELECT DISTINCT {name_col} FROM moves WHERE {name_col} IS NOT NULL ORDER BY 1"  # noqa: S608
        ).fetchall()

        return [r[0] for r in result if r[0]]
    except Exception:
        return []


@st.cache_data
def search_pokemon_by_type_and_move(
    pokemon_type: str | None = None,
    move_name: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Search for Pokemon matching type and/or move criteria.

    Args:
        pokemon_type: Type to filter by (optional).
        move_name: Move the Pokemon must learn (optional).
        db_path: Optional path to database.

    Returns:
        List of dicts with matching Pokemon.
    """
    conn = _get_conn(db_path)

    try:
        # Get pokemon table columns to find type column
        pokemon_cols = conn.execute("PRAGMA table_info('pokemon')").fetchall()
        pokemon_col_names = [c[1] for c in pokemon_cols]
        type_cols = [c for c in pokemon_col_names if "type" in c.lower()]

        # Build query dynamically based on available tables and filters
        tables_available = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

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

        cursor = conn.execute(query, params)
        result = fetchall_to_dicts(cursor)
        return result

    except Exception as e:
        raise e


@st.cache_data
def get_table_preview(table_name: str, limit: int | None = 100, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get a preview of a table's contents.

    Args:
        table_name: Name of the table to preview.
        limit: Maximum rows to return. None for all rows.
        db_path: Optional path to database.

    Returns:
        List of dicts with table contents.
    """
    conn = _get_conn(db_path)

    try:
        # Table name comes from get_table_list() which queries the schema
        if limit is None:
            cursor = conn.execute(f"SELECT * FROM {table_name}")  # noqa: S608
        else:
            cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT ?", [limit])  # noqa: S608
        result = fetchall_to_dicts(cursor)
        return result
    except Exception as e:
        raise e


@st.cache_data
def get_table_list(db_path: Path | None = None) -> list[str]:
    """Get list of available tables in the database.

    Args:
        db_path: Optional path to database.

    Returns:
        List of table names.
    """
    conn = _get_conn(db_path)

    try:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [t[0] for t in tables]
    except Exception:
        return []


@st.cache_data
def get_difficulties(db_path: Path | None = None) -> list[str]:
    """Get list of unique difficulty levels from battles table.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of difficulty levels (excluding None).
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT DISTINCT difficulty FROM battles WHERE difficulty IS NOT NULL ORDER BY difficulty"
        ).fetchall()
        return [r[0] for r in result]
    except Exception:
        return []


@st.cache_data
def get_battles_by_difficulty(difficulty: str | None = None, db_path: Path | None = None) -> list[tuple[int, str]]:
    """Get list of (battle_id, name) tuples, optionally filtered by difficulty.

    Args:
        difficulty: Optional difficulty level to filter by.
        db_path: Optional path to database.

    Returns:
        List of (battle_id, name) tuples sorted by name.
    """
    conn = _get_conn(db_path)

    try:
        if difficulty is None:
            result = conn.execute("SELECT battle_id, name FROM battles ORDER BY name").fetchall()
        else:
            result = conn.execute(
                "SELECT battle_id, name FROM battles WHERE difficulty = ? ORDER BY name",
                [difficulty],
            ).fetchall()
        return [(r[0], r[1]) for r in result]
    except Exception:
        return []


@st.cache_data
def get_battle_by_id(battle_id: int, db_path: Path | None = None) -> dict[str, str | None] | None:
    """Get battle details by ID.

    Args:
        battle_id: ID of the battle.
        db_path: Optional path to database.

    Returns:
        Dictionary with battle details or None if not found.
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            "SELECT battle_id, name, difficulty FROM battles WHERE battle_id = ?",
            [battle_id],
        ).fetchone()
        if result:
            return {
                "battle_id": result[0],
                "name": result[1],
                "difficulty": result[2],
            }
        return None
    except Exception:
        return None


@st.cache_data
def get_battle_team_with_moves(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get a battle's full team with Pokemon types and move details.

    Joins: battles -> battle_pokemon -> pokemon (for types)
           battle_pokemon -> battle_pokemon_moves -> moves (for move types)

    Args:
        battle_id: ID of the battle.
        db_path: Optional path to database.

    Returns:
        List of dicts with battle's team and move information.
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
        FROM battle_pokemon tp
        JOIN pokemon p ON tp.pokemon_key = p.pokemon_key
        JOIN battle_pokemon_moves tpm ON tp.id = tpm.battle_pokemon_id
        JOIN moves m ON tpm.move_key = m.move_key
        WHERE tp.battle_id = ?
        ORDER BY tp.slot, tpm.slot
    """

    try:
        cursor = conn.execute(query, [battle_id])
        result = fetchall_to_dicts(cursor)
        return result
    except Exception as e:
        raise e


@st.cache_data
def get_pre_evolutions(pokemon_name: str, db_path: Path | None = None) -> list[str]:
    """Get all pre-evolutions of a Pokemon using recursive CTE.

    Walks the evolution chain backwards to find all Pokemon that eventually
    evolve into the given Pokemon.

    Args:
        pokemon_name: The Pokemon name to find pre-evolutions for (case-insensitive).
        db_path: Optional path to database.

    Returns:
        List of pre-evolution names, ordered from closest to furthest.
        For "Charizard" returns ["Charmeleon", "Charmander"].
        For Pokemon with no pre-evolutions returns [].
    """
    conn = _get_conn(db_path)

    query = """
    WITH RECURSIVE pre_evos AS (
        SELECT from_pokemon, to_pokemon
        FROM evolutions
        WHERE LOWER(to_pokemon) = LOWER(?)

        UNION ALL

        SELECT e.from_pokemon, e.to_pokemon
        FROM evolutions e
        JOIN pre_evos p ON LOWER(e.to_pokemon) = LOWER(p.from_pokemon)
    )
    SELECT DISTINCT from_pokemon FROM pre_evos
    """

    try:
        result = conn.execute(query, [pokemon_name]).fetchall()
        return [r[0] for r in result]
    except Exception:
        return []


@st.cache_data
def get_all_evolutions(
    pokemon_name: str,
    db_path: Path | None = None,
    level_cap: int | None = None,
) -> list[str]:
    """Get all evolutions of a Pokemon using recursive CTE.

    Walks the evolution chain forward to find all Pokemon that the given
    Pokemon eventually evolves into. If level_cap is provided, only includes
    evolutions that can be achieved at or below that level.

    Args:
        pokemon_name: The Pokemon name to find evolutions for (case-insensitive).
        db_path: Optional path to database.
        level_cap: If set, exclude evolutions requiring level > this value.
            Non-level evolutions (Stone, Trade, etc.) are always included.

    Returns:
        List of evolution names.
        For "Charmander" returns ["Charmeleon", "Charizard"] (or fewer with level_cap).
        For Pokemon with no evolutions returns [].
    """
    conn = _get_conn(db_path)

    if level_cap is None:
        # No level cap - return all evolutions
        query = """
        WITH RECURSIVE evos AS (
            SELECT from_pokemon, to_pokemon
            FROM evolutions
            WHERE LOWER(from_pokemon) = LOWER(?)

            UNION ALL

            SELECT e.from_pokemon, e.to_pokemon
            FROM evolutions e
            JOIN evos ev ON LOWER(e.from_pokemon) = LOWER(ev.to_pokemon)
        )
        SELECT DISTINCT to_pokemon FROM evos
        """
        params: list[str | int] = [pokemon_name]
    else:
        # With level cap - only include evolutions achievable at or below level_cap
        # Level-based evolutions (method = 'Level') must have condition <= level_cap
        # Non-level evolutions (Stone, Trade, etc.) are always included
        query = """
        WITH RECURSIVE evos AS (
            SELECT from_pokemon, to_pokemon, method, condition
            FROM evolutions
            WHERE LOWER(from_pokemon) = LOWER(?)
            AND (
                method != 'Level'
                OR CASE WHEN condition GLOB '[0-9]*' THEN CAST(condition AS INTEGER) ELSE NULL END IS NULL
                OR CASE WHEN condition GLOB '[0-9]*' THEN CAST(condition AS INTEGER) ELSE NULL END <= ?
            )

            UNION ALL

            SELECT e.from_pokemon, e.to_pokemon, e.method, e.condition
            FROM evolutions e
            JOIN evos ev ON LOWER(e.from_pokemon) = LOWER(ev.to_pokemon)
            WHERE (
                e.method != 'Level'
                OR CASE WHEN e.condition GLOB '[0-9]*' THEN CAST(e.condition AS INTEGER) ELSE NULL END IS NULL
                OR CASE WHEN e.condition GLOB '[0-9]*' THEN CAST(e.condition AS INTEGER) ELSE NULL END <= ?
            )
        )
        SELECT DISTINCT to_pokemon FROM evos
        """
        params = [pokemon_name, level_cap, level_cap]

    try:
        result = conn.execute(query, params).fetchall()
        return [r[0] for r in result]
    except Exception:
        return []


@st.cache_data
def get_first_blocked_evolution(
    pokemon_name: str,
    level_cap: int,
    db_path: Path | None = None,
) -> dict[str, str | int] | None:
    """Find the first evolution step blocked by the level cap.

    Walks backward through the evolution chain from the searched Pokemon
    and finds the step closest to the base form where method is 'Level'
    and condition exceeds the level cap.

    Args:
        pokemon_name: The evolved Pokemon name to check (case-insensitive).
        level_cap: The current level cap to check against.
        db_path: Optional path to database.

    Returns:
        Dict with from_pokemon, to_pokemon, level if a blocked step exists,
        or None if no evolution step is blocked by the level cap.
    """
    conn = _get_conn(db_path)

    query = """
    WITH RECURSIVE chain AS (
        SELECT from_pokemon, to_pokemon, method, condition, 1 as depth
        FROM evolutions
        WHERE LOWER(to_pokemon) = LOWER(?)

        UNION ALL

        SELECT e.from_pokemon, e.to_pokemon, e.method, e.condition, c.depth + 1
        FROM evolutions e
        JOIN chain c ON LOWER(e.to_pokemon) = LOWER(c.from_pokemon)
    )
    SELECT from_pokemon, to_pokemon,
           CASE WHEN condition GLOB '[0-9]*' THEN CAST(condition AS INTEGER) ELSE NULL END as level
    FROM chain
    WHERE method = 'Level'
      AND CASE WHEN condition GLOB '[0-9]*' THEN CAST(condition AS INTEGER) ELSE NULL END > ?
    ORDER BY depth DESC
    LIMIT 1
    """

    try:
        result = conn.execute(query, [pokemon_name, level_cap]).fetchone()
        if result is None:
            return None
        return {
            "from_pokemon": result[0],
            "to_pokemon": result[1],
            "level": result[2],
        }
    except Exception:
        return None


@st.cache_data
def get_available_pokemon_set(
    filter_config: "LocationFilterConfig | None",
    db_path: Path | None = None,
) -> frozenset[str] | None:
    """Get set of Pokemon names available given game progress filters.

    Returns Pokemon whose pre-evolution chain has at least one catch location
    passing the filters. Also includes all evolutions of catchable Pokemon.

    Args:
        filter_config: Configuration for location filtering based on game progress.
            If None, returns None to signal that all Pokemon should be included.
        db_path: Optional path to database.

    Returns:
        Frozenset of Pokemon names for O(1) lookup, or None if no filtering should be applied.
    """
    if filter_config is None:
        return None

    # Import here to avoid circular import
    from unbounddb.app.location_filters import apply_location_filters  # noqa: PLC0415

    conn = _get_conn(db_path)

    # Get all locations from DB
    try:
        cursor = conn.execute(
            "SELECT pokemon, location_name, encounter_method, encounter_notes, requirement FROM locations"
        )
        all_locations = fetchall_to_dicts(cursor)
    except Exception:
        return frozenset()

    if not all_locations:
        return frozenset()

    # Apply game progress filters
    filtered = apply_location_filters(all_locations, filter_config)

    if not filtered:
        return frozenset()

    # Get base catchable Pokemon
    catchable = {r["pokemon"] for r in filtered}

    # Add all evolutions of catchable Pokemon (respecting level cap)
    available: set[str] = set()
    for pokemon in catchable:
        available.add(pokemon)
        evolutions = get_all_evolutions(pokemon, db_path, level_cap=filter_config.level_cap)
        available.update(evolutions)

    return frozenset(available)


@st.cache_data
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
        return [r[0] for r in result if r[0]]
    except Exception:
        return []


@st.cache_data
def get_all_pokemon_names_from_locations(db_path: Path | None = None) -> list[str]:
    """Get sorted list of Pokemon names obtainable from catch locations.

    Includes both directly catchable Pokemon and their evolutions, since
    searching for an evolved form will show locations for its pre-evolutions.

    Args:
        db_path: Optional path to database.

    Returns:
        Sorted list of unique Pokemon names (catchable + evolutions).
    """
    conn = _get_conn(db_path)

    try:
        # Use recursive CTE to find all evolutions of catchable Pokemon
        result = conn.execute(
            """
            WITH RECURSIVE
            -- Base: all Pokemon directly in locations table
            catchable AS (
                SELECT DISTINCT pokemon FROM locations WHERE pokemon IS NOT NULL
            ),
            -- Recursive: find all evolutions of catchable Pokemon
            all_evolutions AS (
                -- Start with catchable Pokemon
                SELECT pokemon AS name FROM catchable

                UNION

                -- Add evolutions of Pokemon we've found so far
                SELECT e.to_pokemon AS name
                FROM evolutions e
                JOIN all_evolutions ae ON LOWER(e.from_pokemon) = LOWER(ae.name)
            )
            SELECT DISTINCT name FROM all_evolutions ORDER BY name
            """
        ).fetchall()
        return [r[0] for r in result if r[0]]
    except Exception:
        return []


@st.cache_data
def search_pokemon_locations(pokemon_name: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Search for all locations where a Pokemon or its pre-evolutions can be caught.

    Automatically includes locations for all pre-evolutions of the given Pokemon.
    For example, searching for "Charizard" will also return locations for
    Charmeleon and Charmander.

    Args:
        pokemon_name: The Pokemon name to search for (case-insensitive).
        db_path: Optional path to database.

    Returns:
        List of dicts with columns: pokemon, location_name, encounter_method,
        encounter_notes, requirement. The pokemon column shows which Pokemon
        actually spawns at that location.
    """
    # Get all pre-evolutions
    pre_evos = get_pre_evolutions(pokemon_name, db_path)
    all_pokemon = [pokemon_name, *pre_evos]

    conn = _get_conn(db_path)

    try:
        # Build parameterized query for all Pokemon in the chain
        placeholders = ", ".join(["LOWER(?)" for _ in all_pokemon])
        query = f"""
            SELECT pokemon, location_name, encounter_method, encounter_notes, requirement
            FROM locations
            WHERE LOWER(pokemon) IN ({placeholders})
            ORDER BY pokemon, location_name, encounter_method
        """  # noqa: S608

        cursor = conn.execute(query, all_pokemon)
        result = fetchall_to_dicts(cursor)
        return result
    except Exception as e:
        raise e


@st.cache_data
def get_move_details(move_key: str, db_path: Path | None = None) -> dict[str, str | int | None] | None:
    """Get full details for a move.

    Args:
        move_key: The slugified move key to look up.
        db_path: Optional path to database.

    Returns:
        Dictionary with move details or None if not found.
        Keys: name, type, category, power, accuracy, pp, priority, effect
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            """
            SELECT name, type, category, power, accuracy, pp, priority, effect
            FROM moves
            WHERE move_key = ?
            """,
            [move_key],
        ).fetchone()

        if result:
            return {
                "name": result[0],
                "type": result[1],
                "category": result[2],
                "power": result[3],
                "accuracy": result[4],
                "pp": result[5],
                "priority": result[6],
                "effect": result[7],
            }
        return None
    except Exception:
        return None


@st.cache_data
def get_pokemon_details(pokemon_key: str, db_path: Path | None = None) -> dict[str, str | int | None] | None:
    """Get full stats for a Pokemon.

    Args:
        pokemon_key: The slugified pokemon key to look up.
        db_path: Optional path to database.

    Returns:
        Dictionary with Pokemon details or None if not found.
        Keys: name, hp, attack, defense, sp_attack, sp_defense, speed, bst,
              type1, type2, ability1, ability2, hidden_ability
    """
    conn = _get_conn(db_path)

    try:
        result = conn.execute(
            """
            SELECT name, hp, attack, defense, sp_attack, sp_defense, speed, bst,
                   type1, type2, ability1, ability2, hidden_ability
            FROM pokemon
            WHERE pokemon_key = ?
            """,
            [pokemon_key],
        ).fetchone()

        if result:
            return {
                "name": result[0],
                "hp": result[1],
                "attack": result[2],
                "defense": result[3],
                "sp_attack": result[4],
                "sp_defense": result[5],
                "speed": result[6],
                "bst": result[7],
                "type1": result[8],
                "type2": result[9],
                "ability1": result[10],
                "ability2": result[11],
                "hidden_ability": result[12],
            }
        return None
    except Exception:
        return None


@st.cache_data
def get_pokemon_by_type(
    type_name: str,
    available_pokemon: frozenset[str] | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get all Pokemon of a given type.

    Args:
        type_name: The type to search for (e.g., "Fire", "Water").
        available_pokemon: Optional frozenset of Pokemon names to filter by.
        db_path: Optional path to database.

    Returns:
        List of dicts with columns: name, type1, type2, bst, pokemon_key
        Sorted by bst descending.
    """
    conn = _get_conn(db_path)

    try:
        cursor = conn.execute(
            """
            SELECT name, type1, type2, bst, pokemon_key
            FROM pokemon
            WHERE type1 = ? OR type2 = ?
            ORDER BY bst DESC
            """,
            [type_name, type_name],
        )
        result = fetchall_to_dicts(cursor)

        # Filter by available Pokemon if provided
        if available_pokemon is not None and result:
            result = [r for r in result if r["name"] in available_pokemon]

        return result
    except Exception as e:
        raise e


@st.cache_data
def get_pokemon_learnset(pokemon_key: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get complete learnset for a Pokemon.

    Args:
        pokemon_key: The slugified pokemon key to look up.
        db_path: Optional path to database.

    Returns:
        List of dicts with columns: move_name, move_type, category, power, learn_method, level
        Sorted by learn_method and level.
    """
    conn = _get_conn(db_path)

    try:
        cursor = conn.execute(
            """
            SELECT
                m.name AS move_name,
                m.type AS move_type,
                m.category,
                m.power,
                pm.learn_method,
                pm.level
            FROM pokemon_moves pm
            JOIN moves m ON pm.move_key = m.move_key
            WHERE pm.pokemon_key = ?
            ORDER BY pm.learn_method, pm.level, m.name
            """,
            [pokemon_key],
        )
        result = fetchall_to_dicts(cursor)
        return result
    except Exception as e:
        raise e


def _build_move_conditions(
    filters: "MoveSearchFilters",
    conditions: list[str],
    params: list[Any],
) -> None:
    """Append move-level WHERE clauses for name, type, category, stats, and flags."""
    if filters.move_names:
        placeholders = ", ".join(["?" for _ in filters.move_names])
        conditions.append(f"m.name IN ({placeholders})")
        params.extend(filters.move_names)

    if filters.move_types:
        placeholders = ", ".join(["?" for _ in filters.move_types])
        conditions.append(f"m.type IN ({placeholders})")
        params.extend(filters.move_types)

    if filters.categories:
        placeholders = ", ".join(["?" for _ in filters.categories])
        conditions.append(f"m.category IN ({placeholders})")
        params.extend(filters.categories)

    # Column names are hardcoded constants, safe for f-string
    for col, min_val, max_val in [
        ("power", filters.power_min, filters.power_max),
        ("accuracy", filters.accuracy_min, filters.accuracy_max),
        ("priority", filters.priority_min, filters.priority_max),
        ("pp", filters.pp_min, filters.pp_max),
    ]:
        if min_val is not None:
            conditions.append(f"m.{col} >= ?")
            params.append(min_val)
        if max_val is not None:
            conditions.append(f"m.{col} <= ?")
            params.append(max_val)

    for flag in (
        "makes_contact",
        "is_sound_move",
        "is_punch_move",
        "is_bite_move",
        "is_pulse_move",
        "has_secondary_effect",
    ):
        value = getattr(filters, flag)
        if value is not None:
            conditions.append(f"m.{flag} = ?")
            params.append(1 if value else 0)


def _build_pokemon_conditions(
    filters: "MoveSearchFilters",
    conditions: list[str],
    params: list[Any],
) -> None:
    """Append Pokemon, learn-method, and stat WHERE clauses."""
    if filters.learn_methods:
        placeholders = ", ".join(["?" for _ in filters.learn_methods])
        conditions.append(f"pm.learn_method IN ({placeholders})")
        params.extend(filters.learn_methods)

    if filters.max_learn_level is not None:
        conditions.append("(pm.learn_method != 'level' OR pm.level <= ?)")
        params.append(filters.max_learn_level)

    if filters.stab_only:
        conditions.append("(m.type = p.type1 OR m.type = p.type2)")

    # Column names are hardcoded constants, safe for f-string
    stat_map = {
        "hp": filters.min_hp,
        "attack": filters.min_attack,
        "defense": filters.min_defense,
        "sp_attack": filters.min_sp_attack,
        "sp_defense": filters.min_sp_defense,
        "speed": filters.min_speed,
        "bst": filters.min_bst,
    }
    for col, min_val in stat_map.items():
        if min_val is not None:
            conditions.append(f"p.{col} >= ?")
            params.append(min_val)


def _build_progress_conditions(
    filters: "MoveSearchFilters",
    conditions: list[str],
    params: list[Any],
) -> bool:
    """Append game-progress WHERE clauses. Returns False if query should return empty."""
    if filters.available_pokemon is not None:
        if not filters.available_pokemon:
            return False
        placeholders = ", ".join(["?" for _ in filters.available_pokemon])
        conditions.append(f"p.name IN ({placeholders})")
        params.extend(sorted(filters.available_pokemon))

    if filters.available_tm_keys is not None:
        if not filters.available_tm_keys:
            conditions.append("pm.learn_method != 'tm'")
        else:
            placeholders = ", ".join(["?" for _ in filters.available_tm_keys])
            conditions.append(f"(pm.learn_method != 'tm' OR pm.move_key IN ({placeholders}))")
            params.extend(sorted(filters.available_tm_keys))

    return True


_MOVE_SEARCH_BASE_QUERY = """
    SELECT
        p.name AS pokemon_name, p.pokemon_key,
        p.type1 AS pokemon_type1, p.type2 AS pokemon_type2,
        p.hp, p.attack, p.defense, p.sp_attack, p.sp_defense, p.speed, p.bst,
        p.ability1, p.ability2, p.hidden_ability,
        m.name AS move_name, m.move_key, m.type AS move_type,
        m.category, m.power, m.accuracy, m.pp, m.priority,
        m.has_secondary_effect, m.makes_contact,
        m.is_sound_move, m.is_punch_move, m.is_bite_move, m.is_pulse_move,
        pm.learn_method, pm.level,
        CASE WHEN (m.type = p.type1 OR m.type = p.type2) THEN 1 ELSE 0 END AS is_stab
    FROM pokemon p
    JOIN pokemon_moves pm ON p.pokemon_key = pm.pokemon_key
    JOIN moves m ON pm.move_key = m.move_key
"""


@st.cache_data
def search_moves_advanced(
    filters: "MoveSearchFilters",
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Search Pokemon-move combinations with advanced multi-criteria filters.

    Joins pokemon, pokemon_moves, and moves tables with dynamic WHERE clauses
    built from the filter parameters. Computes STAB indicator in SQL.

    Args:
        filters: Frozen dataclass with all search filter parameters.
        db_path: Optional path to database.

    Returns:
        List of dicts with Pokemon, move, and learn-method details per row.
    """
    conn = _get_conn(db_path)

    conditions: list[str] = []
    params: list[Any] = []

    _build_move_conditions(filters, conditions, params)
    _build_pokemon_conditions(filters, conditions, params)
    if not _build_progress_conditions(filters, conditions, params):
        return []

    query = _MOVE_SEARCH_BASE_QUERY
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY p.bst DESC, p.name ASC, m.power DESC"

    cursor = conn.execute(query, params)
    results = fetchall_to_dicts(cursor)

    for row in results:
        row["is_stab"] = bool(row["is_stab"])

    return results
