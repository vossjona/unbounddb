# ABOUTME: Physical/Special analyzer tool for analyzing trainer matchups.
# ABOUTME: Analyzes whether to prioritize Physical or Special attack/defense.

from pathlib import Path
from typing import Any

import streamlit as st

from unbounddb.app.db import fetchall_to_dicts
from unbounddb.app.queries import _get_conn


@st.cache_data
def get_battle_pokemon_with_stats(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get battle's Pokemon with base stats.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - pokemon_key, slot, attack, defense, sp_attack, sp_defense
    """
    conn = _get_conn(db_path)

    query = """
        SELECT
            tp.pokemon_key,
            tp.slot,
            p.attack,
            p.defense,
            p.sp_attack,
            p.sp_defense
        FROM battle_pokemon tp
        JOIN pokemon p ON tp.pokemon_key = p.pokemon_key
        WHERE tp.battle_id = ?
        ORDER BY tp.slot
    """

    cursor = conn.execute(query, [battle_id])
    result = fetchall_to_dicts(cursor)

    return result


@st.cache_data
def get_battle_pokemon_move_categories(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get battle's Pokemon with their move categories.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - pokemon_key, slot, move_key, move_name, category, power
    """
    conn = _get_conn(db_path)

    query = """
        SELECT
            tp.pokemon_key,
            tp.slot,
            tpm.move_key,
            m.name AS move_name,
            m.category,
            m.power
        FROM battle_pokemon tp
        JOIN battle_pokemon_moves tpm ON tp.id = tpm.battle_pokemon_id
        JOIN moves m ON tpm.move_key = m.move_key
        WHERE tp.battle_id = ?
        ORDER BY tp.slot, tpm.slot
    """

    cursor = conn.execute(query, [battle_id])
    result = fetchall_to_dicts(cursor)

    return result


def classify_pokemon_offensive_profile(pokemon_moves: list[dict[str, Any]]) -> str:
    """Classify a Pokemon's offensive profile based on its moves.

    Args:
        pokemon_moves: List of move dicts with keys: category, power

    Returns:
        "Physical", "Special", or "Mixed"
        - Only Physical moves (category='Physical', power > 0) → "Physical"
        - Only Special moves (category='Special', power > 0) → "Special"
        - Both → "Mixed"
        - Neither (status only) → "Mixed" (default)
    """
    physical_moves = [m for m in pokemon_moves if m.get("category") == "Physical" and (m.get("power") or 0) > 0]
    special_moves = [m for m in pokemon_moves if m.get("category") == "Special" and (m.get("power") or 0) > 0]

    has_physical = len(physical_moves) > 0
    has_special = len(special_moves) > 0

    if has_physical and not has_special:
        return "Physical"
    elif has_special and not has_physical:
        return "Special"
    else:
        return "Mixed"


def classify_pokemon_defensive_profile(defense: int, sp_defense: int) -> str:
    """Classify a Pokemon's defensive profile based on stats.

    Args:
        defense: Defense stat value.
        sp_defense: Special Defense stat value.

    Returns:
        "Physically Defensive", "Specially Defensive", or "Balanced"
        - Defense > Sp.Def * 1.2 → "Physically Defensive"
        - Sp.Def > Defense * 1.2 → "Specially Defensive"
        - Otherwise → "Balanced"
    """
    if defense > sp_defense * 1.2:
        return "Physically Defensive"
    elif sp_defense > defense * 1.2:
        return "Specially Defensive"
    else:
        return "Balanced"


def _group_moves_by_slot(moves_df: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group moves list by Pokemon slot.

    Args:
        moves_df: List of move dicts.

    Returns:
        Dict mapping slot numbers to lists of move dicts.
    """
    pokemon_moves_by_slot: dict[int, list[dict[str, Any]]] = {}
    for row in moves_df:
        slot = row["slot"]
        if slot not in pokemon_moves_by_slot:
            pokemon_moves_by_slot[slot] = []
        pokemon_moves_by_slot[slot].append(
            {
                "move_key": row["move_key"],
                "move_name": row["move_name"],
                "category": row["category"],
                "power": row["power"],
            }
        )
    return pokemon_moves_by_slot


def _get_offensive_recommendation(
    physical_count: int,
    special_count: int,
    total_physical_power: int,
    total_special_power: int,
) -> str:
    """Determine offensive recommendation based on counts and power.

    Args:
        physical_count: Number of Physical attackers.
        special_count: Number of Special attackers.
        total_physical_power: Sum of Physical move power.
        total_special_power: Sum of Special move power.

    Returns:
        Recommendation string.
    """
    if physical_count > special_count and total_physical_power > total_special_power:
        return "Prioritize Defense"
    if special_count > physical_count and total_special_power > total_physical_power:
        return "Prioritize Sp.Def"
    if total_physical_power > total_special_power * 1.5:
        return "Prioritize Defense"
    if total_special_power > total_physical_power * 1.5:
        return "Prioritize Sp.Def"
    return "Balance both"


def _build_pokemon_offensive_detail(
    row: dict[str, Any],
    moves: list[dict[str, Any]],
) -> tuple[dict[str, Any], int, int]:
    """Build offensive detail for a single Pokemon.

    Args:
        row: Pokemon stats row.
        moves: List of Pokemon's moves.

    Returns:
        Tuple of (detail dict, physical power sum, special power sum).
    """
    profile = classify_pokemon_offensive_profile(moves)

    physical_moves = [m for m in moves if m.get("category") == "Physical" and (m.get("power") or 0) > 0]
    special_moves = [m for m in moves if m.get("category") == "Special" and (m.get("power") or 0) > 0]

    phys_power = sum(m.get("power") or 0 for m in physical_moves)
    spec_power = sum(m.get("power") or 0 for m in special_moves)

    detail = {
        "pokemon_key": row["pokemon_key"],
        "slot": row["slot"],
        "attack": row["attack"],
        "sp_attack": row["sp_attack"],
        "profile": profile,
        "physical_moves": [m["move_name"] for m in physical_moves],
        "special_moves": [m["move_name"] for m in special_moves],
    }

    return detail, phys_power, spec_power


def _empty_offensive_profile() -> dict[str, Any]:
    """Return empty offensive profile result."""
    return {
        "physical_count": 0,
        "special_count": 0,
        "mixed_count": 0,
        "total_physical_power": 0,
        "total_special_power": 0,
        "avg_team_attack": 0.0,
        "avg_team_sp_attack": 0.0,
        "recommendation": "No data available",
        "pokemon_details": [],
    }


@st.cache_data
def analyze_battle_offensive_profile(battle_id: int, db_path: Path | None = None) -> dict[str, Any]:
    """Analyze what type of attacking moves the battle uses.

    This tells us whether to prioritize Defense or Sp.Defense.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        Dict with:
        - physical_count: int (Pokemon that are Physical attackers)
        - special_count: int (Pokemon that are Special attackers)
        - mixed_count: int (Pokemon that are Mixed attackers)
        - total_physical_power: int (sum of Physical move power)
        - total_special_power: int (sum of Special move power)
        - avg_team_attack: float
        - avg_team_sp_attack: float
        - recommendation: str ("Prioritize Defense" / "Prioritize Sp.Def" / "Balance both")
        - pokemon_details: list[dict] (per-Pokemon breakdown)
    """
    moves_df = get_battle_pokemon_move_categories(battle_id, db_path)
    stats_df = get_battle_pokemon_with_stats(battle_id, db_path)

    if not moves_df or not stats_df:
        return _empty_offensive_profile()

    pokemon_moves_by_slot = _group_moves_by_slot(moves_df)

    pokemon_details: list[dict[str, Any]] = []
    profile_counts = {"Physical": 0, "Special": 0, "Mixed": 0}
    total_physical_power = 0
    total_special_power = 0

    for row in stats_df:
        moves = pokemon_moves_by_slot.get(row["slot"], [])
        detail, phys_power, spec_power = _build_pokemon_offensive_detail(row, moves)

        profile_counts[detail["profile"]] += 1
        total_physical_power += phys_power
        total_special_power += spec_power
        pokemon_details.append(detail)

    avg_team_attack = sum(r["attack"] for r in stats_df) / len(stats_df)
    avg_team_sp_attack = sum(r["sp_attack"] for r in stats_df) / len(stats_df)

    recommendation = _get_offensive_recommendation(
        profile_counts["Physical"],
        profile_counts["Special"],
        total_physical_power,
        total_special_power,
    )

    return {
        "physical_count": profile_counts["Physical"],
        "special_count": profile_counts["Special"],
        "mixed_count": profile_counts["Mixed"],
        "total_physical_power": total_physical_power,
        "total_special_power": total_special_power,
        "avg_team_attack": round(avg_team_attack, 1),
        "avg_team_sp_attack": round(avg_team_sp_attack, 1),
        "recommendation": recommendation,
        "pokemon_details": pokemon_details,
    }


@st.cache_data
def analyze_battle_defensive_profile(battle_id: int, db_path: Path | None = None) -> dict[str, Any]:
    """Analyze what defensive stats the battle's team has.

    This tells us whether to use Physical or Special moves.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        Dict with:
        - physically_defensive_count: int
        - specially_defensive_count: int
        - balanced_count: int
        - avg_team_defense: float
        - avg_team_sp_defense: float
        - recommendation: str ("Use Physical moves" / "Use Special moves" / "Either works")
        - pokemon_details: list[dict] (per-Pokemon breakdown)
    """
    stats_df = get_battle_pokemon_with_stats(battle_id, db_path)

    # Handle empty results
    if not stats_df:
        return {
            "physically_defensive_count": 0,
            "specially_defensive_count": 0,
            "balanced_count": 0,
            "avg_team_defense": 0.0,
            "avg_team_sp_defense": 0.0,
            "recommendation": "No data available",
            "pokemon_details": [],
        }

    # Build Pokemon details
    pokemon_details: list[dict[str, Any]] = []
    physically_defensive_count = 0
    specially_defensive_count = 0
    balanced_count = 0

    for row in stats_df:
        pokemon_key = row["pokemon_key"]
        slot = row["slot"]
        defense = row["defense"]
        sp_defense = row["sp_defense"]

        profile = classify_pokemon_defensive_profile(defense, sp_defense)

        # Count profile types
        if profile == "Physically Defensive":
            physically_defensive_count += 1
        elif profile == "Specially Defensive":
            specially_defensive_count += 1
        else:
            balanced_count += 1

        pokemon_details.append(
            {
                "pokemon_key": pokemon_key,
                "slot": slot,
                "defense": defense,
                "sp_defense": sp_defense,
                "profile": profile,
            }
        )

    # Calculate team averages
    avg_team_defense = sum(r["defense"] for r in stats_df) / len(stats_df)
    avg_team_sp_defense = sum(r["sp_defense"] for r in stats_df) / len(stats_df)

    # Determine recommendation
    # If they have more specially defensive Pokemon, use Physical moves
    # If they have more physically defensive Pokemon, use Special moves
    if physically_defensive_count > specially_defensive_count:
        recommendation = "Use Special moves"
    elif specially_defensive_count > physically_defensive_count:
        recommendation = "Use Physical moves"
    elif avg_team_defense > avg_team_sp_defense * 1.2:
        recommendation = "Use Special moves"
    elif avg_team_sp_defense > avg_team_defense * 1.2:
        recommendation = "Use Physical moves"
    else:
        recommendation = "Either works"

    return {
        "physically_defensive_count": physically_defensive_count,
        "specially_defensive_count": specially_defensive_count,
        "balanced_count": balanced_count,
        "avg_team_defense": round(avg_team_defense, 1),
        "avg_team_sp_defense": round(avg_team_sp_defense, 1),
        "recommendation": recommendation,
        "pokemon_details": pokemon_details,
    }
