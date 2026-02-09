# ABOUTME: Offensive type suggester tool for analyzing trainer matchups.
# ABOUTME: Suggests optimal attacking types and 4-type coverage against trainer teams.

from itertools import combinations
from pathlib import Path
from typing import Any, TypedDict

import polars as pl

from unbounddb.app.queries import _get_conn
from unbounddb.utils.type_chart import (
    IMMUNITY_VALUE,
    NEUTRAL_VALUE,
    SUPER_EFFECTIVE_THRESHOLD,
    TYPES,
    get_effectiveness,
)

# Threshold for 4x effectiveness (2x * 2x)
SUPER_EFFECTIVE_4X_THRESHOLD = 4.0


class EffectivenessResult(TypedDict):
    """Result of attack effectiveness calculation."""

    effectiveness: float
    category: str


def get_battle_pokemon_types(battle_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Get battle's Pokemon with their types.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with keys: slot, pokemon_key, type1, type2
    """
    conn = _get_conn(db_path)

    query = """
        SELECT
            tp.slot,
            tp.pokemon_key,
            p.type1,
            p.type2
        FROM battle_pokemon tp
        JOIN pokemon p ON tp.pokemon_key = p.pokemon_key
        WHERE tp.battle_id = ?
        ORDER BY tp.slot
    """

    result = conn.execute(query, [battle_id]).fetchall()
    conn.close()

    return [
        {
            "slot": row[0],
            "pokemon_key": row[1],
            "type1": row[2],
            "type2": row[3],
        }
        for row in result
    ]


# Alias for internal use
_build_battle_pokemon_types = get_battle_pokemon_types


def _calculate_attack_effectiveness(atk_type: str, def_type1: str, def_type2: str | None) -> EffectivenessResult:
    """Calculate offensive effectiveness with category label.

    Args:
        atk_type: The attacking type.
        def_type1: Defender's primary type.
        def_type2: Defender's secondary type (or None).

    Returns:
        EffectivenessResult with effectiveness (float) and category (str)
    """
    effectiveness = get_effectiveness(atk_type, def_type1, def_type2)

    if effectiveness == IMMUNITY_VALUE:
        category = "immune"
    elif effectiveness >= SUPER_EFFECTIVE_4X_THRESHOLD:
        category = "4x"
    elif effectiveness >= SUPER_EFFECTIVE_THRESHOLD:
        category = "2x"
    elif effectiveness == NEUTRAL_VALUE:
        category = "neutral"
    else:
        category = "resisted"

    return {"effectiveness": effectiveness, "category": category}


def _score_single_type(atk_type: str, pokemon_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Score a single attacking type against a Pokemon list.

    Scoring formula:
        score = 4x_count * 8 + 2x_count * 4 - resisted_count * 2 - immune_count * 6

    Args:
        atk_type: The attacking type to score.
        pokemon_list: List of trainer Pokemon with type info.

    Returns:
        Dict with type, 4x/2x/neutral/resisted/immune counts, score
    """
    counts = {"4x": 0, "2x": 0, "neutral": 0, "resisted": 0, "immune": 0}

    for pkmn in pokemon_list:
        result = _calculate_attack_effectiveness(atk_type, pkmn["type1"], pkmn["type2"])
        counts[result["category"]] += 1

    score = counts["4x"] * 8 + counts["2x"] * 4 - counts["resisted"] * 2 - counts["immune"] * 6

    return {
        "type": atk_type,
        "4x_count": counts["4x"],
        "2x_count": counts["2x"],
        "neutral_count": counts["neutral"],
        "resisted_count": counts["resisted"],
        "immune_count": counts["immune"],
        "score": score,
    }


def analyze_single_type_offense(battle_id: int, db_path: Path | None = None) -> pl.DataFrame:
    """Analyze all 18 types ranked by offensive effectiveness against a battle.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.

    Returns:
        DataFrame with columns: type, 4x_count, 2x_count, neutral_count,
        resisted_count, immune_count, score
        Sorted by score DESC
    """
    pokemon_list = _build_battle_pokemon_types(battle_id, db_path)

    if not pokemon_list:
        return pl.DataFrame(
            schema={
                "type": pl.String,
                "4x_count": pl.Int64,
                "2x_count": pl.Int64,
                "neutral_count": pl.Int64,
                "resisted_count": pl.Int64,
                "immune_count": pl.Int64,
                "score": pl.Int64,
            }
        )

    results = [_score_single_type(atk_type, pokemon_list) for atk_type in TYPES]

    df = pl.DataFrame(results)
    return df.sort("score", descending=True)


def _score_type_combo(
    types: tuple[str, ...],
    pokemon_list: list[dict[str, Any]],
    effectiveness_cache: dict[tuple[str, str], float],
) -> dict[str, Any]:
    """Score a 4-type combination for coverage.

    A Pokemon is 'covered' if at least one type hits it >= 2x.

    Scoring formula:
        score = pokemon_covered * 10 + sum_of_best_effectiveness * 2 - uncovered_count * 15

    Args:
        types: Tuple of 4 attacking types.
        pokemon_list: List of trainer Pokemon with type info.
        effectiveness_cache: Pre-computed effectiveness values.

    Returns:
        Dict with types, covered_count, total_pokemon, coverage_pct, score
    """
    covered_count = 0
    sum_best_effectiveness = 0.0

    for pkmn in pokemon_list:
        pokemon_key = pkmn["pokemon_key"]
        best_eff = 0.0

        for atk_type in types:
            eff = effectiveness_cache[(atk_type, pokemon_key)]
            best_eff = max(best_eff, eff)

        if best_eff >= SUPER_EFFECTIVE_THRESHOLD:
            covered_count += 1
        sum_best_effectiveness += best_eff

    total_pokemon = len(pokemon_list)
    uncovered_count = total_pokemon - covered_count

    score = int(covered_count * 10 + sum_best_effectiveness * 2 - uncovered_count * 15)

    coverage_pct = (covered_count / total_pokemon * 100) if total_pokemon > 0 else 0

    return {
        "types": ", ".join(types),
        "types_tuple": types,
        "covered_count": covered_count,
        "total_pokemon": total_pokemon,
        "coverage_pct": round(coverage_pct, 1),
        "score": score,
    }


def analyze_four_type_coverage(battle_id: int, db_path: Path | None = None, top_n: int = 50) -> pl.DataFrame:
    """Find best 4-type combinations for coverage. Evaluates all 3060 combos.

    Args:
        battle_id: ID of the battle to analyze.
        db_path: Optional path to database.
        top_n: Number of top results to return.

    Returns:
        DataFrame with columns: types, covered_count, total_pokemon, coverage_pct, score
        Sorted by score DESC
    """
    pokemon_list = _build_battle_pokemon_types(battle_id, db_path)

    if not pokemon_list:
        return pl.DataFrame(
            schema={
                "types": pl.String,
                "covered_count": pl.Int64,
                "total_pokemon": pl.Int64,
                "coverage_pct": pl.Float64,
                "score": pl.Int64,
            }
        )

    # Pre-compute effectiveness for all (type, pokemon) pairs
    effectiveness_cache: dict[tuple[str, str], float] = {}
    for atk_type in TYPES:
        for pkmn in pokemon_list:
            effectiveness_cache[(atk_type, pkmn["pokemon_key"])] = get_effectiveness(
                atk_type, pkmn["type1"], pkmn["type2"]
            )

    # Evaluate all C(18, 4) = 3060 combinations
    results = [_score_type_combo(combo, pokemon_list, effectiveness_cache) for combo in combinations(TYPES, 4)]

    # Sort and return top N
    results.sort(key=lambda x: x["score"], reverse=True)

    # Remove internal tuple before creating DataFrame
    for r in results:
        del r["types_tuple"]

    df = pl.DataFrame(results[:top_n])
    return df


def get_type_coverage_detail(battle_id: int, atk_types: list[str], db_path: Path | None = None) -> pl.DataFrame:
    """Get per-Pokemon breakdown for attacking types.

    Args:
        battle_id: ID of the battle to analyze.
        atk_types: List of attacking types to analyze.
        db_path: Optional path to database.

    Returns:
        DataFrame with columns: pokemon_key, slot, type1, type2,
        best_type, best_effectiveness, is_covered
    """
    pokemon_list = _build_battle_pokemon_types(battle_id, db_path)

    if not pokemon_list:
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "slot": pl.Int64,
                "type1": pl.String,
                "type2": pl.String,
                "best_type": pl.String,
                "best_effectiveness": pl.Float64,
                "is_covered": pl.Boolean,
            }
        )

    results: list[dict[str, Any]] = []

    for pkmn in pokemon_list:
        best_type = ""
        best_eff = 0.0

        for atk_type in atk_types:
            eff = get_effectiveness(atk_type, pkmn["type1"], pkmn["type2"])
            if eff > best_eff:
                best_eff = eff
                best_type = atk_type

        results.append(
            {
                "pokemon_key": pkmn["pokemon_key"],
                "slot": pkmn["slot"],
                "type1": pkmn["type1"],
                "type2": pkmn["type2"],
                "best_type": best_type,
                "best_effectiveness": best_eff,
                "is_covered": best_eff >= SUPER_EFFECTIVE_THRESHOLD,
            }
        )

    df = pl.DataFrame(results)
    return df.sort("slot")


def get_single_type_detail(battle_id: int, atk_type: str, db_path: Path | None = None) -> pl.DataFrame:
    """Get per-Pokemon breakdown for a single attacking type.

    Args:
        battle_id: ID of the battle to analyze.
        atk_type: The attacking type to analyze.
        db_path: Optional path to database.

    Returns:
        DataFrame with columns: pokemon_key, slot, type1, type2,
        effectiveness, category
    """
    pokemon_list = _build_battle_pokemon_types(battle_id, db_path)

    if not pokemon_list:
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "slot": pl.Int64,
                "type1": pl.String,
                "type2": pl.String,
                "effectiveness": pl.Float64,
                "category": pl.String,
            }
        )

    results: list[dict[str, Any]] = []

    for pkmn in pokemon_list:
        eff_result = _calculate_attack_effectiveness(atk_type, pkmn["type1"], pkmn["type2"])

        results.append(
            {
                "pokemon_key": pkmn["pokemon_key"],
                "slot": pkmn["slot"],
                "type1": pkmn["type1"],
                "type2": pkmn["type2"],
                "effectiveness": eff_result["effectiveness"],
                "category": eff_result["category"],
            }
        )

    df = pl.DataFrame(results)
    return df.sort("slot")
