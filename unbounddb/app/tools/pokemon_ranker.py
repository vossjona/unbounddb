# ABOUTME: Pokemon ranker tool for ranking Pokemon against battle matchups.
# ABOUTME: Combines defensive typing, offensive moves, and stat alignment into a composite score.

from pathlib import Path
from typing import Any

import streamlit as st

from unbounddb.app.queries import _get_conn
from unbounddb.app.tools.defensive_suggester import get_battle_move_types
from unbounddb.app.tools.offensive_suggester import analyze_single_type_offense, get_battle_pokemon_types
from unbounddb.app.tools.phys_spec_analyzer import analyze_battle_defensive_profile
from unbounddb.build.database import fetchall_to_dicts
from unbounddb.utils.type_chart import (
    IMMUNITY_VALUE,
    RESISTANCE_THRESHOLD,
    SUPER_EFFECTIVE_THRESHOLD,
    TYPES,
    get_effectiveness,
)

# Set of valid types for quick lookup
VALID_TYPES = set(TYPES)


@st.cache_data
def get_all_pokemon_with_stats(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Batch query all Pokemon with their stats and types.

    Args:
        db_path: Optional path to database.

    Returns:
        List of dicts with keys:
        - pokemon_key, name, type1, type2, attack, sp_attack, defense, sp_defense, speed, bst
    """
    conn = _get_conn(db_path)

    query = """
        SELECT pokemon_key, name, type1, type2,
               attack, sp_attack, defense, sp_defense, speed, bst
        FROM pokemon
        ORDER BY name
    """

    cursor = conn.execute(query)
    result = fetchall_to_dicts(cursor)

    return result


@st.cache_data
def get_all_learnable_offensive_moves(
    db_path: Path | None = None,
    available_tm_keys: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Batch query all offensive moves that Pokemon can learn.

    Excludes tutor moves since they have no structured location data
    for availability checking. Optionally filters TM moves to only
    include those whose TMs are obtainable at current game progress.

    Args:
        db_path: Optional path to database.
        available_tm_keys: Optional set of move keys for obtainable TMs.
            If provided, TM moves not in this set are excluded.
            If None, all TM moves are included.

    Returns:
        List of dicts with keys:
        - pokemon_key, move_key, move_name, move_type, category, power, learn_method, level
    """
    conn = _get_conn(db_path)

    query = """
        SELECT pm.pokemon_key, pm.move_key, pm.learn_method, pm.level,
               m.name AS move_name, m.type AS move_type, m.category, m.power
        FROM pokemon_moves pm
        JOIN moves m ON pm.move_key = m.move_key
        WHERE m.power > 0
          AND m.category IN ('Physical', 'Special')
          AND pm.learn_method != 'tutor'
        ORDER BY pm.pokemon_key, m.power DESC
    """

    cursor = conn.execute(query)
    result = fetchall_to_dicts(cursor)

    # Filter out TM moves that aren't obtainable at current progression
    if available_tm_keys is not None and result:
        result = [r for r in result if r["learn_method"] != "tm" or r["move_key"] in available_tm_keys]

    return result


@st.cache_data
def get_recommended_types(
    battle_id: int,
    top_n: int = 4,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get top N offensive types from analyze_single_type_offense().

    Args:
        battle_id: ID of the battle to analyze.
        top_n: Number of top types to return (default 4).
        db_path: Optional path to database.

    Returns:
        List of dicts with keys: type, score, rank (1-indexed)
    """
    single_type_df = analyze_single_type_offense(battle_id, db_path)

    if not single_type_df:
        return []

    results: list[dict[str, Any]] = []
    for i, row in enumerate(single_type_df[:top_n]):
        results.append(
            {
                "type": row["type"],
                "score": row["score"],
                "rank": i + 1,
            }
        )

    return results


def calculate_defense_score(
    type1: str,
    type2: str | None,
    battle_move_types: list[str],
) -> tuple[float, list[str], list[str], list[str]]:
    """Calculate defense score for a Pokemon's typing against battle's move types.

    The raw score formula:
        immunity_count * 3 + resistance_count * 2 - weakness_count * 4

    This is then normalized to a 0-100 scale based on expected score range.

    Args:
        type1: Pokemon's primary type.
        type2: Pokemon's secondary type (or None for monotype).
        battle_move_types: List of move types the battle uses.

    Returns:
        Tuple of (normalized_score, immunities, resistances, weaknesses)
    """
    if not battle_move_types:
        return 0.0, [], [], []

    # Skip Pokemon with non-standard types (e.g., Mystery)
    if type1 not in VALID_TYPES:
        return 0.0, [], [], []
    if type2 is not None and type2 not in VALID_TYPES:
        return 0.0, [], [], []

    immunities: list[str] = []
    resistances: list[str] = []
    weaknesses: list[str] = []

    for move_type in battle_move_types:
        # Skip non-standard move types
        if move_type not in VALID_TYPES:
            continue
        effectiveness = get_effectiveness(move_type, type1, type2)

        if effectiveness == IMMUNITY_VALUE:
            immunities.append(move_type)
        elif effectiveness <= RESISTANCE_THRESHOLD:
            resistances.append(move_type)
        elif effectiveness >= SUPER_EFFECTIVE_THRESHOLD:
            weaknesses.append(move_type)

    # Calculate raw score
    raw_score = len(immunities) * 3 + len(resistances) * 2 - len(weaknesses) * 4

    # Normalize to 0-100 scale
    # Max theoretical: All types immune (18 * 3 = 54)
    # Min theoretical: All types weak (18 * -4 = -72)
    # We use a practical range based on typical battle teams (6-10 move types)
    # Max expected: ~30 (10 immunities/resistances), Min expected: ~-40 (10 weaknesses)
    min_score = -40
    max_score = 30
    normalized = ((raw_score - min_score) / (max_score - min_score)) * 100
    normalized = max(0.0, min(100.0, normalized))  # Clamp to 0-100

    return normalized, immunities, resistances, weaknesses


def calculate_offense_score(
    learnable_moves: list[dict[str, Any]],
    recommended_types: list[dict[str, Any]],
    pokemon_type1: str,
    pokemon_type2: str | None,
    battle_pokemon: list[dict[str, Any]] | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate offense score based on learnable moves of recommended types.

    Includes moves that are either:
    1. One of the top recommended types against the battle, OR
    2. Super-effective against any of the battle's Pokemon

    Scoring for each qualifying move:
        type_rank_bonus = (5 - type_rank) * 2  # Rank 1-4 gives bonus 8,6,4,2 (0 for non-ranked)
        stab_bonus = 5 if move.type in [pokemon.type1, pokemon.type2] else 0
        power_bonus = move.power / 20  # 100 power = 5 points

    Score is capped at 100.

    Args:
        learnable_moves: List of dicts of moves the Pokemon can learn.
        recommended_types: List of dicts with type and rank.
        pokemon_type1: Pokemon's primary type.
        pokemon_type2: Pokemon's secondary type (or None).
        battle_pokemon: Optional list of battle Pokemon dicts with type1, type2.

    Returns:
        Tuple of (score, good_moves_list)
        good_moves_list: List of dicts with move details and effective power
    """
    if not learnable_moves:
        return 0.0, []

    # Build type -> rank lookup
    type_to_rank = {rt["type"]: rt["rank"] for rt in recommended_types}
    recommended_type_set = set(type_to_rank.keys())

    # Pokemon's types for STAB calculation
    pokemon_types = {pokemon_type1}
    if pokemon_type2:
        pokemon_types.add(pokemon_type2)

    score = 0.0
    good_moves: list[dict[str, Any]] = []
    seen_moves: set[str] = set()

    for row in learnable_moves:
        move_type = row["move_type"]
        move_key = row["move_key"]

        # Skip if already seen
        if move_key in seen_moves:
            continue

        # Check if move qualifies: recommended type OR super-effective against battle
        is_recommended = move_type in recommended_type_set
        is_super_effective = False

        if battle_pokemon and move_type in VALID_TYPES:
            for battle_pkmn in battle_pokemon:
                eff = get_effectiveness(move_type, battle_pkmn["type1"], battle_pkmn["type2"])
                if eff >= SUPER_EFFECTIVE_THRESHOLD:
                    is_super_effective = True
                    break

        if not is_recommended and not is_super_effective:
            continue

        seen_moves.add(move_key)

        power = row["power"] or 0
        category = row["category"]
        is_stab = move_type in pokemon_types

        # Calculate bonuses
        type_rank = type_to_rank.get(move_type, 5)  # Default rank 5 for non-recommended types
        type_rank_bonus = max(0, (5 - type_rank) * 2)  # 8, 6, 4, 2 for ranks 1-4, 0 for rank 5+
        stab_bonus = 5 if is_stab else 0
        power_bonus = power / 20  # 100 power = 5 points

        move_score = type_rank_bonus + stab_bonus + power_bonus
        score += move_score

        # Effective power for display (STAB multiplier)
        effective_power = int(power * 1.5) if is_stab else power

        good_moves.append(
            {
                "move_name": row["move_name"],
                "move_key": move_key,
                "move_type": move_type,
                "power": power,
                "category": category,
                "is_stab": is_stab,
                "effective_power": effective_power,
                "type_rank": type_rank,
                "learn_method": row["learn_method"],
                "level": row["level"],
            }
        )

    # Sort good moves: STAB first, then by type rank, then by effective power
    good_moves.sort(
        key=lambda m: (
            not m["is_stab"],  # False < True, so STAB (True) comes first
            m["type_rank"],  # Lower rank is better
            -m["effective_power"],  # Higher power is better
        )
    )

    # Diversify moves for better type coverage (max 3 per type, 15 total)
    diversified_moves = _diversify_moves(good_moves)

    # Cap score at 100
    final_score = min(score, 100.0)

    return final_score, diversified_moves


def calculate_stat_score(
    attack: int,
    sp_attack: int,
    phys_spec_recommendation: str,
) -> float:
    """Calculate stat alignment score based on physical/special recommendation.

    Args:
        attack: Pokemon's Attack stat.
        sp_attack: Pokemon's Special Attack stat.
        phys_spec_recommendation: "Use Physical moves", "Use Special moves", or "Either works"

    Returns:
        Score from 0-100 based on how well the Pokemon's stats match the recommendation.
    """
    # Normalize stats to 0-100 scale (typical range is ~20-190)
    # Using 190 as practical max for base stats
    max_stat = 190

    normalized_attack = min((attack / max_stat) * 100, 100.0)
    normalized_sp_attack = min((sp_attack / max_stat) * 100, 100.0)

    if phys_spec_recommendation == "Use Physical moves":
        return normalized_attack
    elif phys_spec_recommendation == "Use Special moves":
        return normalized_sp_attack
    else:  # "Either works" or any other value
        return (normalized_attack + normalized_sp_attack) / 2


def calculate_bst_score(bst: int) -> float:
    """Calculate BST score normalized to 0-100.

    Args:
        bst: Base Stat Total.

    Returns:
        Score from 0-100. Practical range 300-600, legendaries cap at 100.
    """
    min_bst = 300  # Weak Pokemon floor
    max_bst = 600  # Strong non-legendary ceiling

    normalized = ((bst - min_bst) / (max_bst - min_bst)) * 100
    return max(0.0, min(100.0, normalized))


def calculate_coverage(
    learnable_moves: list[dict[str, Any]],
    battle_pokemon: list[dict[str, Any]],
) -> tuple[list[str], int]:
    """Calculate which battle Pokemon can be hit super-effectively.

    Args:
        learnable_moves: Pokemon's learnable moves (with move_type column).
        battle_pokemon: List of battle Pokemon dicts with type1, type2, pokemon_key.

    Returns:
        Tuple of (covered_pokemon_keys, coverage_count)
        covered_pokemon_keys: List of pokemon_key strings that are covered
    """
    if not learnable_moves or not battle_pokemon:
        return [], 0

    # Extract unique move types from learnable moves
    move_types = list({r["move_type"] for r in learnable_moves})

    covered_keys: list[str] = []

    for battle_pkmn in battle_pokemon:
        pokemon_key = battle_pkmn["pokemon_key"]
        type1 = battle_pkmn["type1"]
        type2 = battle_pkmn["type2"]

        # Check if any move type is super-effective (>=2x) against this Pokemon
        for move_type in move_types:
            if move_type not in VALID_TYPES:
                continue
            effectiveness = get_effectiveness(move_type, type1, type2)
            if effectiveness >= SUPER_EFFECTIVE_THRESHOLD:
                covered_keys.append(pokemon_key)
                break  # Once covered, no need to check other move types

    return covered_keys, len(covered_keys)


MAX_MOVES_PER_TYPE = 3
MAX_TOTAL_MOVES = 15


def _diversify_moves(
    good_moves: list[dict[str, Any]],
    max_per_type: int = MAX_MOVES_PER_TYPE,
    max_total: int = MAX_TOTAL_MOVES,
) -> list[dict[str, Any]]:
    """Diversify moves to show better type coverage.

    Limits moves per type and interleaves types for better spread.

    Args:
        good_moves: List of good move dicts (already sorted by STAB/rank/power).
        max_per_type: Maximum moves to include per type.
        max_total: Maximum total moves to return.

    Returns:
        Diversified list of moves with better type coverage.
    """
    if not good_moves:
        return []

    # Group moves by type, preserving original sort order within each type
    moves_by_type: dict[str, list[dict[str, Any]]] = {}
    for move in good_moves:
        move_type = move["move_type"]
        if move_type not in moves_by_type:
            moves_by_type[move_type] = []
        if len(moves_by_type[move_type]) < max_per_type:
            moves_by_type[move_type].append(move)

    # Get type order by best type_rank (lowest rank = best), then by having STAB
    type_order = sorted(
        moves_by_type.keys(),
        key=lambda t: (
            min(m["type_rank"] for m in moves_by_type[t]),
            not any(m["is_stab"] for m in moves_by_type[t]),  # STAB types first
        ),
    )

    # Interleave: take one from each type in round-robin fashion
    result: list[dict[str, Any]] = []
    type_indices: dict[str, int] = dict.fromkeys(type_order, 0)

    while len(result) < max_total:
        added_any = False
        for move_type in type_order:
            if len(result) >= max_total:
                break
            idx = type_indices[move_type]
            if idx < len(moves_by_type[move_type]):
                result.append(moves_by_type[move_type][idx])
                type_indices[move_type] = idx + 1
                added_any = True
        if not added_any:
            break  # All types exhausted

    return result


def _get_top_moves_string(good_moves: list[dict[str, Any]], limit: int = 5) -> str:
    """Format top moves as a comma-separated string.

    Args:
        good_moves: List of good move dicts (already diversified).
        limit: Maximum number of moves to include.

    Returns:
        Formatted string like "Earthquake, Iron Head, Rock Slide"
    """
    if not good_moves:
        return "-"

    move_names = [m["move_name"] for m in good_moves[:limit]]
    return ", ".join(move_names)


@st.cache_data
def rank_pokemon_for_battle(
    battle_id: int,
    db_path: Path | None = None,
    top_n: int = 50,
    available_pokemon: frozenset[str] | None = None,
    available_tm_keys: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Rank all Pokemon for a battle matchup using composite scoring.

    Scoring weights:
        defense_score * 0.30 + offense_score * 0.40 + stat_score * 0.15 + bst_score * 0.15

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.
        top_n: Number of top results to return (0 for all).
        available_pokemon: Optional set of Pokemon names to filter by. If provided,
            only Pokemon in this set will be included in the rankings.
        available_tm_keys: Optional set of move keys for obtainable TMs.
            If provided, TM moves not in this set are excluded from scoring.

    Returns:
        List of dicts with keys:
        - rank, pokemon_key, name, type1, type2, bst
        - total_score, defense_score, offense_score, stat_score, bst_score
        - immunities, resistances, weaknesses (comma-separated strings)
        - top_moves (comma-separated string)
        - covers (comma-separated list of covered battle Pokemon)
        - coverage_count (integer count of covered Pokemon)
    """
    # Get battle analysis data
    move_types = get_battle_move_types(battle_id, db_path)
    recommended_types = get_recommended_types(battle_id, top_n=4, db_path=db_path)
    defensive_profile = analyze_battle_defensive_profile(battle_id, db_path)
    phys_spec_rec = defensive_profile.get("recommendation", "Either works")
    battle_pokemon = get_battle_pokemon_types(battle_id, db_path)

    # Get all Pokemon and moves
    all_pokemon = get_all_pokemon_with_stats(db_path)
    all_moves = get_all_learnable_offensive_moves(db_path, available_tm_keys=available_tm_keys)

    # Filter by available Pokemon if specified
    if available_pokemon is not None:
        all_pokemon = [r for r in all_pokemon if r["name"] in available_pokemon]

    if not all_pokemon:
        return []

    # Group moves by pokemon_key for efficient lookup
    moves_by_pokemon: dict[str, list[dict[str, Any]]] = {}
    if all_moves:
        for move in all_moves:
            pk = move["pokemon_key"]
            if pk not in moves_by_pokemon:
                moves_by_pokemon[pk] = []
            moves_by_pokemon[pk].append(move)

    # Score each Pokemon
    results: list[dict[str, Any]] = []
    total_battle_pokemon = len(battle_pokemon)

    for row in all_pokemon:
        pokemon_key = row["pokemon_key"]
        type1 = row["type1"]
        type2 = row["type2"]
        attack = row["attack"]
        sp_attack = row["sp_attack"]
        bst = row["bst"]

        # Defense score
        defense_score, immunities, resistances, weaknesses = calculate_defense_score(type1, type2, move_types)

        # Offense score
        pokemon_moves = moves_by_pokemon.get(pokemon_key, [])
        offense_score, good_moves = calculate_offense_score(
            pokemon_moves,
            recommended_types,
            type1,
            type2,
            battle_pokemon,
        )

        # Stat score
        stat_score = calculate_stat_score(attack, sp_attack, phys_spec_rec)

        # BST score
        bst_score = calculate_bst_score(bst)

        # Coverage calculation
        covered_keys, coverage_count = calculate_coverage(pokemon_moves, battle_pokemon)

        # Composite score with new weights
        total_score = defense_score * 0.30 + offense_score * 0.40 + stat_score * 0.15 + bst_score * 0.15

        # Format coverage string
        covers_str = f"{coverage_count}/{total_battle_pokemon}" if coverage_count > 0 else "0"

        results.append(
            {
                "pokemon_key": pokemon_key,
                "name": row["name"],
                "type1": type1,
                "type2": type2,
                "bst": bst,
                "total_score": round(total_score, 1),
                "defense_score": round(defense_score, 1),
                "offense_score": round(offense_score, 1),
                "stat_score": round(stat_score, 1),
                "bst_score": round(bst_score, 1),
                "immunities": ", ".join(immunities) if immunities else "-",
                "resistances": ", ".join(resistances) if resistances else "-",
                "weaknesses": ", ".join(weaknesses) if weaknesses else "-",
                "top_moves": _get_top_moves_string(good_moves),
                "covers": covers_str,
                "coverage_count": coverage_count,
                "covered_pokemon": covered_keys,  # Keep full list for UI detail
            }
        )

    # Sort by total score
    results.sort(key=lambda r: r["total_score"], reverse=True)

    # Add rank column
    for i, result in enumerate(results):
        result["rank"] = i + 1

    if top_n > 0:
        results = results[:top_n]

    return results


@st.cache_data
def get_pokemon_moves_detail(
    pokemon_key: str,
    battle_id: int,
    db_path: Path | None = None,
    available_tm_keys: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Get detailed good moves for a specific Pokemon against a battle.

    Args:
        pokemon_key: The Pokemon's key.
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.
        available_tm_keys: Optional set of move keys for obtainable TMs.

    Returns:
        List of dicts with move details:
        - move_name, move_type, power, category, is_stab, effective_power
        - learn_method, level, type_rank
    """
    # Get Pokemon's types
    conn = _get_conn(db_path)
    query = "SELECT type1, type2 FROM pokemon WHERE pokemon_key = ?"
    result = conn.execute(query, [pokemon_key]).fetchone()

    if not result:
        return []

    pokemon_type1, pokemon_type2 = result

    # Get recommended types and battle Pokemon
    recommended_types = get_recommended_types(battle_id, top_n=4, db_path=db_path)
    battle_pokemon = get_battle_pokemon_types(battle_id, db_path)

    # Get Pokemon's learnable moves
    all_moves = get_all_learnable_offensive_moves(db_path, available_tm_keys=available_tm_keys)
    pokemon_moves = [m for m in all_moves if m["pokemon_key"] == pokemon_key]

    if not pokemon_moves:
        return []

    # Calculate offense score to get good moves list
    _, good_moves = calculate_offense_score(
        pokemon_moves,
        recommended_types,
        pokemon_type1,
        pokemon_type2,
        battle_pokemon,
    )

    return good_moves


@st.cache_data
def get_coverage_detail(
    pokemon_key: str,
    battle_id: int,
    db_path: Path | None = None,
    available_tm_keys: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Get detailed coverage breakdown for a Pokemon against battle's team.

    Args:
        pokemon_key: The Pokemon's key.
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.
        available_tm_keys: Optional set of move keys for obtainable TMs.

    Returns:
        List of dicts with coverage details per battle Pokemon:
        - pokemon_key, type1, type2, is_covered, best_move_type, effectiveness
    """
    # Get battle's Pokemon
    battle_pokemon = get_battle_pokemon_types(battle_id, db_path)

    if not battle_pokemon:
        return []

    # Get Pokemon's learnable moves
    all_moves = get_all_learnable_offensive_moves(db_path, available_tm_keys=available_tm_keys)
    pokemon_moves = [m for m in all_moves if m["pokemon_key"] == pokemon_key]

    if not pokemon_moves:
        # No moves - none covered
        return [
            {
                "pokemon_key": tp["pokemon_key"],
                "type1": tp["type1"],
                "type2": tp["type2"],
                "is_covered": False,
                "best_move_type": None,
                "effectiveness": 1.0,
            }
            for tp in battle_pokemon
        ]

    # Extract unique move types
    move_types = list({r["move_type"] for r in pokemon_moves})

    results: list[dict[str, Any]] = []

    for battle_pkmn in battle_pokemon:
        pkmn_key = battle_pkmn["pokemon_key"]
        type1 = battle_pkmn["type1"]
        type2 = battle_pkmn["type2"]

        best_eff = 0.0
        best_type = None

        for move_type in move_types:
            if move_type not in VALID_TYPES:
                continue
            eff = get_effectiveness(move_type, type1, type2)
            if eff > best_eff:
                best_eff = eff
                best_type = move_type

        results.append(
            {
                "pokemon_key": pkmn_key,
                "type1": type1,
                "type2": type2,
                "is_covered": best_eff >= SUPER_EFFECTIVE_THRESHOLD,
                "best_move_type": best_type,
                "effectiveness": best_eff,
            }
        )

    return results
