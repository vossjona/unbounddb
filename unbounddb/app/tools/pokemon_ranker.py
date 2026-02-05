# ABOUTME: Pokemon ranker tool for ranking Pokemon against trainer matchups.
# ABOUTME: Combines defensive typing, offensive moves, and stat alignment into a composite score.

from pathlib import Path
from typing import Any

import polars as pl

from unbounddb.app.queries import _get_conn
from unbounddb.app.tools.defensive_suggester import get_trainer_move_types
from unbounddb.app.tools.offensive_suggester import analyze_single_type_offense, get_trainer_pokemon_types
from unbounddb.app.tools.phys_spec_analyzer import analyze_trainer_defensive_profile
from unbounddb.utils.type_chart import (
    IMMUNITY_VALUE,
    RESISTANCE_THRESHOLD,
    SUPER_EFFECTIVE_THRESHOLD,
    TYPES,
    get_effectiveness,
)

# Set of valid types for quick lookup
VALID_TYPES = set(TYPES)


def get_all_pokemon_with_stats(db_path: Path | None = None) -> pl.DataFrame:
    """Batch query all Pokemon with their stats and types.

    Args:
        db_path: Optional path to database.

    Returns:
        DataFrame with columns:
        - pokemon_key, name, type1, type2, attack, sp_attack, defense, sp_defense, speed, bst
    """
    conn = _get_conn(db_path)

    query = """
        SELECT pokemon_key, name, type1, type2,
               attack, sp_attack, defense, sp_defense, speed, bst
        FROM pokemon
        ORDER BY name
    """

    result = conn.execute(query).pl()
    conn.close()

    return result


def get_all_learnable_offensive_moves(db_path: Path | None = None) -> pl.DataFrame:
    """Batch query all offensive moves that Pokemon can learn.

    Args:
        db_path: Optional path to database.

    Returns:
        DataFrame with columns:
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
        ORDER BY pm.pokemon_key, m.power DESC
    """

    result = conn.execute(query).pl()
    conn.close()

    return result


def get_recommended_types(
    trainer_id: int,
    top_n: int = 4,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get top N offensive types from analyze_single_type_offense().

    Args:
        trainer_id: ID of the trainer to analyze.
        top_n: Number of top types to return (default 4).
        db_path: Optional path to database.

    Returns:
        List of dicts with keys: type, score, rank (1-indexed)
    """
    single_type_df = analyze_single_type_offense(trainer_id, db_path)

    if single_type_df.is_empty():
        return []

    results: list[dict[str, Any]] = []
    for i, row in enumerate(single_type_df.head(top_n).iter_rows(named=True)):
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
    trainer_move_types: list[str],
) -> tuple[float, list[str], list[str], list[str]]:
    """Calculate defense score for a Pokemon's typing against trainer's move types.

    The raw score formula:
        immunity_count * 3 + resistance_count * 2 - weakness_count * 4

    This is then normalized to a 0-100 scale based on expected score range.

    Args:
        type1: Pokemon's primary type.
        type2: Pokemon's secondary type (or None for monotype).
        trainer_move_types: List of move types the trainer uses.

    Returns:
        Tuple of (normalized_score, immunities, resistances, weaknesses)
    """
    if not trainer_move_types:
        return 0.0, [], [], []

    # Skip Pokemon with non-standard types (e.g., Mystery)
    if type1 not in VALID_TYPES:
        return 0.0, [], [], []
    if type2 is not None and type2 not in VALID_TYPES:
        return 0.0, [], [], []

    immunities: list[str] = []
    resistances: list[str] = []
    weaknesses: list[str] = []

    for move_type in trainer_move_types:
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
    # We use a practical range based on typical trainer teams (6-10 move types)
    # Max expected: ~30 (10 immunities/resistances), Min expected: ~-40 (10 weaknesses)
    min_score = -40
    max_score = 30
    normalized = ((raw_score - min_score) / (max_score - min_score)) * 100
    normalized = max(0.0, min(100.0, normalized))  # Clamp to 0-100

    return normalized, immunities, resistances, weaknesses


def calculate_offense_score(
    learnable_moves: pl.DataFrame,
    recommended_types: list[dict[str, Any]],
    pokemon_type1: str,
    pokemon_type2: str | None,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate offense score based on learnable moves of recommended types.

    Scoring for each qualifying move:
        type_rank_bonus = (5 - type_rank) * 2  # Rank 1-4 gives bonus 8,6,4,2
        stab_bonus = 5 if move.type in [pokemon.type1, pokemon.type2] else 0
        power_bonus = move.power / 20  # 100 power = 5 points

    Score is capped at 100.

    Args:
        learnable_moves: DataFrame of moves the Pokemon can learn.
        recommended_types: List of dicts with type and rank.
        pokemon_type1: Pokemon's primary type.
        pokemon_type2: Pokemon's secondary type (or None).

    Returns:
        Tuple of (score, good_moves_list)
        good_moves_list: List of dicts with move details and effective power
    """
    if learnable_moves.is_empty() or not recommended_types:
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

    for row in learnable_moves.iter_rows(named=True):
        move_type = row["move_type"]
        move_key = row["move_key"]

        # Skip if not a recommended type or already seen
        if move_type not in recommended_type_set or move_key in seen_moves:
            continue

        seen_moves.add(move_key)

        power = row["power"] or 0
        category = row["category"]
        is_stab = move_type in pokemon_types

        # Calculate bonuses
        type_rank = type_to_rank[move_type]
        type_rank_bonus = (5 - type_rank) * 2  # 8, 6, 4, 2 for ranks 1-4
        stab_bonus = 5 if is_stab else 0
        power_bonus = power / 20  # 100 power = 5 points

        move_score = type_rank_bonus + stab_bonus + power_bonus
        score += move_score

        # Effective power for display (STAB multiplier)
        effective_power = int(power * 1.5) if is_stab else power

        good_moves.append(
            {
                "move_name": row["move_name"],
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

    # Cap score at 100
    final_score = min(score, 100.0)

    return final_score, good_moves


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
    learnable_moves: pl.DataFrame,
    trainer_pokemon: list[dict[str, Any]],
) -> tuple[list[str], int]:
    """Calculate which trainer Pokemon can be hit super-effectively.

    Args:
        learnable_moves: Pokemon's learnable moves (with move_type column).
        trainer_pokemon: List of trainer Pokemon dicts with type1, type2, pokemon_key.

    Returns:
        Tuple of (covered_pokemon_keys, coverage_count)
        covered_pokemon_keys: List of pokemon_key strings that are covered
    """
    if learnable_moves.is_empty() or not trainer_pokemon:
        return [], 0

    # Extract unique move types from learnable moves
    move_types = set(learnable_moves["move_type"].unique().to_list())

    covered_keys: list[str] = []

    for trainer_pkmn in trainer_pokemon:
        pokemon_key = trainer_pkmn["pokemon_key"]
        type1 = trainer_pkmn["type1"]
        type2 = trainer_pkmn["type2"]

        # Check if any move type is super-effective (>=2x) against this Pokemon
        for move_type in move_types:
            if move_type not in VALID_TYPES:
                continue
            effectiveness = get_effectiveness(move_type, type1, type2)
            if effectiveness >= SUPER_EFFECTIVE_THRESHOLD:
                covered_keys.append(pokemon_key)
                break  # Once covered, no need to check other move types

    return covered_keys, len(covered_keys)


def _get_top_moves_string(good_moves: list[dict[str, Any]], limit: int = 3) -> str:
    """Format top moves as a comma-separated string.

    Args:
        good_moves: List of good move dicts (already sorted).
        limit: Maximum number of moves to include.

    Returns:
        Formatted string like "Earthquake, Iron Head, Rock Slide"
    """
    if not good_moves:
        return "-"

    move_names = [m["move_name"] for m in good_moves[:limit]]
    return ", ".join(move_names)


def rank_pokemon_for_trainer(
    trainer_id: int,
    db_path: Path | None = None,
    top_n: int = 50,
    available_pokemon: set[str] | None = None,
) -> pl.DataFrame:
    """Rank all Pokemon for a trainer matchup using composite scoring.

    Scoring weights:
        defense_score * 0.30 + offense_score * 0.40 + stat_score * 0.15 + bst_score * 0.15

    Args:
        trainer_id: ID of the trainer to analyze.
        db_path: Optional path to database.
        top_n: Number of top results to return (0 for all).
        available_pokemon: Optional set of Pokemon names to filter by. If provided,
            only Pokemon in this set will be included in the rankings.

    Returns:
        DataFrame with columns:
        - rank, pokemon_key, name, type1, type2, bst
        - total_score, defense_score, offense_score, stat_score, bst_score
        - immunities, resistances, weaknesses (comma-separated strings)
        - top_moves (comma-separated string)
        - covers (comma-separated list of covered trainer Pokemon)
        - coverage_count (integer count of covered Pokemon)
    """
    # Get trainer analysis data
    move_types = get_trainer_move_types(trainer_id, db_path)
    recommended_types = get_recommended_types(trainer_id, top_n=4, db_path=db_path)
    defensive_profile = analyze_trainer_defensive_profile(trainer_id, db_path)
    phys_spec_rec = defensive_profile.get("recommendation", "Either works")
    trainer_pokemon = get_trainer_pokemon_types(trainer_id, db_path)

    # Get all Pokemon and moves
    all_pokemon = get_all_pokemon_with_stats(db_path)
    all_moves = get_all_learnable_offensive_moves(db_path)

    # Filter by available Pokemon if specified
    if available_pokemon is not None:
        all_pokemon = all_pokemon.filter(pl.col("name").is_in(available_pokemon))

    if all_pokemon.is_empty():
        return pl.DataFrame(
            schema={
                "rank": pl.Int64,
                "pokemon_key": pl.String,
                "name": pl.String,
                "type1": pl.String,
                "type2": pl.String,
                "bst": pl.Int64,
                "total_score": pl.Float64,
                "defense_score": pl.Float64,
                "offense_score": pl.Float64,
                "stat_score": pl.Float64,
                "bst_score": pl.Float64,
                "immunities": pl.String,
                "resistances": pl.String,
                "weaknesses": pl.String,
                "top_moves": pl.String,
                "covers": pl.String,
                "coverage_count": pl.Int64,
            }
        )

    # Group moves by pokemon_key for efficient lookup
    moves_by_pokemon: dict[str, pl.DataFrame] = {}
    if not all_moves.is_empty():
        for pokemon_key in all_pokemon["pokemon_key"].unique().to_list():
            pokemon_moves = all_moves.filter(pl.col("pokemon_key") == pokemon_key)
            if not pokemon_moves.is_empty():
                moves_by_pokemon[pokemon_key] = pokemon_moves

    # Score each Pokemon
    results: list[dict[str, Any]] = []
    total_trainer_pokemon = len(trainer_pokemon)

    for row in all_pokemon.iter_rows(named=True):
        pokemon_key = row["pokemon_key"]
        type1 = row["type1"]
        type2 = row["type2"]
        attack = row["attack"]
        sp_attack = row["sp_attack"]
        bst = row["bst"]

        # Defense score
        defense_score, immunities, resistances, weaknesses = calculate_defense_score(type1, type2, move_types)

        # Offense score
        pokemon_moves = moves_by_pokemon.get(pokemon_key, pl.DataFrame())
        offense_score, good_moves = calculate_offense_score(
            pokemon_moves,
            recommended_types,
            type1,
            type2,
        )

        # Stat score
        stat_score = calculate_stat_score(attack, sp_attack, phys_spec_rec)

        # BST score
        bst_score = calculate_bst_score(bst)

        # Coverage calculation
        covered_keys, coverage_count = calculate_coverage(pokemon_moves, trainer_pokemon)

        # Composite score with new weights
        total_score = defense_score * 0.30 + offense_score * 0.40 + stat_score * 0.15 + bst_score * 0.15

        # Format coverage string
        covers_str = f"{coverage_count}/{total_trainer_pokemon}" if coverage_count > 0 else "0"

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

    # Create DataFrame and sort by total score
    df = pl.DataFrame(results)
    df = df.sort("total_score", descending=True)

    # Add rank column
    df = df.with_row_index("rank", offset=1)

    # Reorder columns
    df = df.select(
        [
            "rank",
            "pokemon_key",
            "name",
            "type1",
            "type2",
            "bst",
            "total_score",
            "defense_score",
            "offense_score",
            "stat_score",
            "bst_score",
            "immunities",
            "resistances",
            "weaknesses",
            "top_moves",
            "covers",
            "coverage_count",
            "covered_pokemon",
        ]
    )

    if top_n > 0:
        df = df.head(top_n)

    return df


def get_pokemon_moves_detail(
    pokemon_key: str,
    trainer_id: int,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get detailed good moves for a specific Pokemon against a trainer.

    Args:
        pokemon_key: The Pokemon's key.
        trainer_id: ID of the trainer to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with move details:
        - move_name, move_type, power, category, is_stab, effective_power
        - learn_method, level, type_rank
    """
    # Get Pokemon's types
    conn = _get_conn(db_path)
    query = "SELECT type1, type2 FROM pokemon WHERE pokemon_key = ?"
    result = conn.execute(query, [pokemon_key]).fetchone()
    conn.close()

    if not result:
        return []

    pokemon_type1, pokemon_type2 = result

    # Get recommended types
    recommended_types = get_recommended_types(trainer_id, top_n=4, db_path=db_path)

    # Get Pokemon's learnable moves
    all_moves = get_all_learnable_offensive_moves(db_path)
    pokemon_moves = all_moves.filter(pl.col("pokemon_key") == pokemon_key)

    if pokemon_moves.is_empty():
        return []

    # Calculate offense score to get good moves list
    _, good_moves = calculate_offense_score(
        pokemon_moves,
        recommended_types,
        pokemon_type1,
        pokemon_type2,
    )

    return good_moves


def get_coverage_detail(
    pokemon_key: str,
    trainer_id: int,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Get detailed coverage breakdown for a Pokemon against trainer's team.

    Args:
        pokemon_key: The Pokemon's key.
        trainer_id: ID of the trainer to analyze.
        db_path: Optional path to database.

    Returns:
        List of dicts with coverage details per trainer Pokemon:
        - pokemon_key, type1, type2, is_covered, best_move_type, effectiveness
    """
    # Get trainer's Pokemon
    trainer_pokemon = get_trainer_pokemon_types(trainer_id, db_path)

    if not trainer_pokemon:
        return []

    # Get Pokemon's learnable moves
    all_moves = get_all_learnable_offensive_moves(db_path)
    pokemon_moves = all_moves.filter(pl.col("pokemon_key") == pokemon_key)

    if pokemon_moves.is_empty():
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
            for tp in trainer_pokemon
        ]

    # Extract unique move types
    move_types = set(pokemon_moves["move_type"].unique().to_list())

    results: list[dict[str, Any]] = []

    for trainer_pkmn in trainer_pokemon:
        pkmn_key = trainer_pkmn["pokemon_key"]
        type1 = trainer_pkmn["type1"]
        type2 = trainer_pkmn["type2"]

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
