# ABOUTME: Defensive type suggester tool for analyzing trainer matchups.
# ABOUTME: Suggests optimal defensive type combinations against trainer teams.

from pathlib import Path
from typing import Any

import streamlit as st

from unbounddb.app.queries import _get_conn
from unbounddb.build.database import fetchall_to_dicts
from unbounddb.utils.type_chart import (
    generate_all_type_combinations,
    get_effectiveness,
    score_defensive_typing,
)


def _count_neutralized_pokemon(
    pokemon_by_slot: dict[int, list[str]],
    def_type1: str,
    def_type2: str | None,
) -> int:
    """Count how many Pokemon are neutralized by a defensive typing.

    A Pokemon is neutralized if none of their moves are super-effective.

    Args:
        pokemon_by_slot: Dict mapping slot numbers to lists of move types.
        def_type1: Defensive type 1.
        def_type2: Defensive type 2 (or None for monotype).

    Returns:
        Number of Pokemon that are neutralized.
    """
    neutralized_count = 0
    for their_move_types in pokemon_by_slot.values():
        is_neutralized = all(
            get_effectiveness(move_type, def_type1, def_type2) <= 1.0 for move_type in their_move_types
        )
        if is_neutralized:
            neutralized_count += 1
    return neutralized_count


def _build_pokemon_move_types(pokemon_moves_df: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Build a mapping of Pokemon slots to their offensive move types.

    Args:
        pokemon_moves_df: List of dicts with pokemon moves data.

    Returns:
        Dict mapping slot numbers to lists of unique move types.
    """
    pokemon_by_slot: dict[int, list[str]] = {}
    for row in pokemon_moves_df:
        slot = row["slot"]
        move_type = row["move_type"]
        category = row["move_category"]

        # Only count offensive moves (Physical/Special)
        if category != "Status" and move_type:
            if slot not in pokemon_by_slot:
                pokemon_by_slot[slot] = []
            if move_type not in pokemon_by_slot[slot]:
                pokemon_by_slot[slot].append(move_type)
    return pokemon_by_slot


def _score_type_combination(
    def_type1: str,
    def_type2: str | None,
    move_types: list[str],
    pokemon_by_slot: dict[int, list[str]],
) -> dict[str, Any]:
    """Score a single defensive type combination.

    Args:
        def_type1: Defensive type 1.
        def_type2: Defensive type 2 (or None for monotype).
        move_types: List of attacking move types.
        pokemon_by_slot: Dict mapping slot numbers to move types.

    Returns:
        Dict with scoring data for this type combination.
    """
    scoring = score_defensive_typing(def_type1, def_type2, move_types)
    neutralized_count = _count_neutralized_pokemon(pokemon_by_slot, def_type1, def_type2)

    score = (
        scoring["immunity_count"] * 3
        + scoring["resistance_count"] * 2
        + neutralized_count * 5
        - scoring["weakness_count"] * 4
    )

    return {
        "type1": def_type1,
        "type2": def_type2,
        "immunity_count": scoring["immunity_count"],
        "resistance_count": scoring["resistance_count"],
        "neutral_count": scoring["neutral_count"],
        "weakness_count": scoring["weakness_count"],
        "pokemon_neutralized": neutralized_count,
        "immunities_list": ", ".join(scoring["immunities"]) if scoring["immunities"] else "-",
        "resistances_list": ", ".join(scoring["resistances"]) if scoring["resistances"] else "-",
        "weaknesses_list": ", ".join(scoring["weaknesses"]) if scoring["weaknesses"] else "-",
        "score": score,
    }


@st.cache_data
def get_battle_move_types(battle_id: int, db_path: Path | None = None) -> list[str]:
    """Get unique offensive move types from a battle's team.

    Filters out Status moves (only Physical/Special count).
    Returns title-case types matching type_chart format.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of unique move types (title case, e.g., "Fire", "Water").
    """
    conn = _get_conn(db_path)

    query = """
        SELECT DISTINCT m.type AS move_type
        FROM battle_pokemon tp
        JOIN battle_pokemon_moves tpm ON tp.id = tpm.battle_pokemon_id
        JOIN moves m ON tpm.move_key = m.move_key
        WHERE tp.battle_id = ?
          AND m.category != 'Status'
          AND m.type IS NOT NULL
        ORDER BY m.type
    """

    result = conn.execute(query, [battle_id]).fetchall()

    return [row[0] for row in result]


@st.cache_data
def get_battle_pokemon_with_moves(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get battle's Pokemon with their moves and types.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - pokemon_key, slot, type1, type2, move_key, move_name, move_type, move_category
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

    cursor = conn.execute(query, [battle_id])
    result = fetchall_to_dicts(cursor)

    return result


@st.cache_data
def analyze_battle_defense(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Analyze all 171 type combinations against a battle's team.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - type1, type2 (defensive typing)
        - immunity_count, resistance_count, neutral_count, weakness_count
        - pokemon_neutralized (count of battle Pokemon with no super-effective moves)
        - immunities_list, resistances_list (for detail display)
        - score (composite ranking score)

        Sorted by: score DESC
    """
    # Get the battle's move types
    move_types = get_battle_move_types(battle_id, db_path)

    if not move_types:
        return []

    # Get Pokemon with their moves for neutralization calculation
    pokemon_moves_df = get_battle_pokemon_with_moves(battle_id, db_path)
    pokemon_by_slot = _build_pokemon_move_types(pokemon_moves_df)

    # Analyze all 171 type combinations
    all_combos = generate_all_type_combinations()
    results = [
        _score_type_combination(def_type1, def_type2, move_types, pokemon_by_slot)
        for def_type1, def_type2 in all_combos
    ]

    return sorted(results, key=lambda r: r["score"], reverse=True)


@st.cache_data
def get_neutralized_pokemon_detail(
    battle_id: int,
    def_type1: str,
    def_type2: str | None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get detail of which battle Pokemon are neutralized by a defensive typing.

    Args:
        battle_id: ID of the battle to analyze.
        def_type1: Defensive type 1.
        def_type2: Defensive type 2 (or None for monotype).
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - pokemon_key, slot, pokemon_type1, pokemon_type2
        - best_move, best_move_type, best_effectiveness
        - is_neutralized (True if best_effectiveness <= 1.0)
    """
    pokemon_moves_df = get_battle_pokemon_with_moves(battle_id, db_path)

    if not pokemon_moves_df:
        return []

    # Group by Pokemon and find their best move
    results: list[dict[str, Any]] = []
    seen_slots: set[int] = set()

    for row in pokemon_moves_df:
        slot = row["slot"]
        pokemon_key = row["pokemon_key"]
        pokemon_type1 = row["pokemon_type1"]
        pokemon_type2 = row["pokemon_type2"]
        move_name = row["move_name"]
        move_type = row["move_type"]
        category = row["move_category"]

        # Skip Status moves
        if category == "Status" or not move_type:
            continue

        effectiveness = get_effectiveness(move_type, def_type1, def_type2)

        # Check if this Pokemon slot already exists
        if slot not in seen_slots:
            seen_slots.add(slot)
            results.append(
                {
                    "pokemon_key": pokemon_key,
                    "slot": slot,
                    "pokemon_type1": pokemon_type1,
                    "pokemon_type2": pokemon_type2,
                    "best_move": move_name,
                    "best_move_type": move_type,
                    "best_effectiveness": effectiveness,
                }
            )
        else:
            # Update if this move is better
            for r in results:
                if r["slot"] == slot and effectiveness > r["best_effectiveness"]:
                    r["best_move"] = move_name
                    r["best_move_type"] = move_type
                    r["best_effectiveness"] = effectiveness
                    break

    # Add is_neutralized flag
    for r in results:
        r["is_neutralized"] = r["best_effectiveness"] <= 1.0

    return sorted(results, key=lambda r: r["slot"])
