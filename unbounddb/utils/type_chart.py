# ABOUTME: Pokemon type effectiveness chart for Gen 6+ (18 types including Fairy).
# ABOUTME: Provides functions to calculate type matchups and defensive scores.

from typing import Any

# Effectiveness thresholds
SUPER_EFFECTIVE_THRESHOLD = 2.0
RESISTANCE_THRESHOLD = 0.5
NEUTRAL_VALUE = 1.0
IMMUNITY_VALUE = 0.0

TYPES: list[str] = [
    "Normal",
    "Fire",
    "Water",
    "Electric",
    "Grass",
    "Ice",
    "Fighting",
    "Poison",
    "Ground",
    "Flying",
    "Psychic",
    "Bug",
    "Rock",
    "Ghost",
    "Dragon",
    "Dark",
    "Steel",
    "Fairy",
]

# 18x18 effectiveness matrix: EFFECTIVENESS[attacking_type][defending_type]
EFFECTIVENESS: dict[str, dict[str, float]] = {
    "Normal": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 0.5,
        "Ghost": 0.0,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Fire": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 0.5,
        "Electric": 1.0,
        "Grass": 2.0,
        "Ice": 2.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 2.0,
        "Rock": 0.5,
        "Ghost": 1.0,
        "Dragon": 0.5,
        "Dark": 1.0,
        "Steel": 2.0,
        "Fairy": 1.0,
    },
    "Water": {
        "Normal": 1.0,
        "Fire": 2.0,
        "Water": 0.5,
        "Electric": 1.0,
        "Grass": 0.5,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 2.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 2.0,
        "Ghost": 1.0,
        "Dragon": 0.5,
        "Dark": 1.0,
        "Steel": 1.0,
        "Fairy": 1.0,
    },
    "Electric": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 2.0,
        "Electric": 0.5,
        "Grass": 0.5,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 0.0,
        "Flying": 2.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 0.5,
        "Dark": 1.0,
        "Steel": 1.0,
        "Fairy": 1.0,
    },
    "Grass": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 2.0,
        "Electric": 1.0,
        "Grass": 0.5,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 0.5,
        "Ground": 2.0,
        "Flying": 0.5,
        "Psychic": 1.0,
        "Bug": 0.5,
        "Rock": 2.0,
        "Ghost": 1.0,
        "Dragon": 0.5,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Ice": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 0.5,
        "Electric": 1.0,
        "Grass": 2.0,
        "Ice": 0.5,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 2.0,
        "Flying": 2.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 2.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Fighting": {
        "Normal": 2.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 2.0,
        "Fighting": 1.0,
        "Poison": 0.5,
        "Ground": 1.0,
        "Flying": 0.5,
        "Psychic": 0.5,
        "Bug": 0.5,
        "Rock": 2.0,
        "Ghost": 0.0,
        "Dragon": 1.0,
        "Dark": 2.0,
        "Steel": 2.0,
        "Fairy": 0.5,
    },
    "Poison": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 2.0,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 0.5,
        "Ground": 0.5,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 0.5,
        "Ghost": 0.5,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 0.0,
        "Fairy": 2.0,
    },
    "Ground": {
        "Normal": 1.0,
        "Fire": 2.0,
        "Water": 1.0,
        "Electric": 2.0,
        "Grass": 0.5,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 2.0,
        "Ground": 1.0,
        "Flying": 0.0,
        "Psychic": 1.0,
        "Bug": 0.5,
        "Rock": 2.0,
        "Ghost": 1.0,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 2.0,
        "Fairy": 1.0,
    },
    "Flying": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 0.5,
        "Grass": 2.0,
        "Ice": 1.0,
        "Fighting": 2.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 2.0,
        "Rock": 0.5,
        "Ghost": 1.0,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Psychic": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 2.0,
        "Poison": 2.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 0.5,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 1.0,
        "Dark": 0.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Bug": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 2.0,
        "Ice": 1.0,
        "Fighting": 0.5,
        "Poison": 0.5,
        "Ground": 1.0,
        "Flying": 0.5,
        "Psychic": 2.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 0.5,
        "Dragon": 1.0,
        "Dark": 2.0,
        "Steel": 0.5,
        "Fairy": 0.5,
    },
    "Rock": {
        "Normal": 1.0,
        "Fire": 2.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 2.0,
        "Fighting": 0.5,
        "Poison": 1.0,
        "Ground": 0.5,
        "Flying": 2.0,
        "Psychic": 1.0,
        "Bug": 2.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
    "Ghost": {
        "Normal": 0.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 2.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 2.0,
        "Dragon": 1.0,
        "Dark": 0.5,
        "Steel": 1.0,
        "Fairy": 1.0,
    },
    "Dragon": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 2.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 0.0,
    },
    "Dark": {
        "Normal": 1.0,
        "Fire": 1.0,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 0.5,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 2.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 2.0,
        "Dragon": 1.0,
        "Dark": 0.5,
        "Steel": 1.0,
        "Fairy": 0.5,
    },
    "Steel": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 0.5,
        "Electric": 0.5,
        "Grass": 1.0,
        "Ice": 2.0,
        "Fighting": 1.0,
        "Poison": 1.0,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 2.0,
        "Ghost": 1.0,
        "Dragon": 1.0,
        "Dark": 1.0,
        "Steel": 0.5,
        "Fairy": 2.0,
    },
    "Fairy": {
        "Normal": 1.0,
        "Fire": 0.5,
        "Water": 1.0,
        "Electric": 1.0,
        "Grass": 1.0,
        "Ice": 1.0,
        "Fighting": 2.0,
        "Poison": 0.5,
        "Ground": 1.0,
        "Flying": 1.0,
        "Psychic": 1.0,
        "Bug": 1.0,
        "Rock": 1.0,
        "Ghost": 1.0,
        "Dragon": 2.0,
        "Dark": 2.0,
        "Steel": 0.5,
        "Fairy": 1.0,
    },
}


def get_effectiveness(atk_type: str, def_type1: str, def_type2: str | None = None) -> float:
    """Calculate type effectiveness multiplier.

    Args:
        atk_type: The attacking type (e.g., "Fire").
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.

    Returns:
        Effectiveness multiplier: 0, 0.25, 0.5, 1, 2, or 4.

    Note:
        If def_type1 == def_type2, the multiplier is calculated only once
        (e.g., Water vs Fire/Fire = 2x, NOT 4x).
    """
    multiplier = EFFECTIVENESS[atk_type][def_type1]

    # Only apply second type if it exists AND is different from the first
    if def_type2 is not None and def_type2 != def_type1:
        multiplier *= EFFECTIVENESS[atk_type][def_type2]

    return multiplier


def get_weaknesses(def_type1: str, def_type2: str | None = None) -> list[str]:
    """Return types that are super effective (>=2x) against the defender.

    Args:
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.

    Returns:
        List of attacking types at >=2x effectiveness.
    """
    return [
        atk_type for atk_type in TYPES if get_effectiveness(atk_type, def_type1, def_type2) >= SUPER_EFFECTIVE_THRESHOLD
    ]


def get_resistances(def_type1: str, def_type2: str | None = None) -> list[str]:
    """Return types that are resisted (<=0.5x, excluding 0x) by the defender.

    Args:
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.

    Returns:
        List of attacking types at <=0.5x effectiveness (excluding immunities).
    """
    return [
        atk_type
        for atk_type in TYPES
        if IMMUNITY_VALUE < get_effectiveness(atk_type, def_type1, def_type2) <= RESISTANCE_THRESHOLD
    ]


def get_immunities(def_type1: str, def_type2: str | None = None) -> list[str]:
    """Return types that the defender is immune to (0x effectiveness).

    Args:
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.

    Returns:
        List of attacking types at 0x effectiveness.
    """
    return [atk_type for atk_type in TYPES if get_effectiveness(atk_type, def_type1, def_type2) == IMMUNITY_VALUE]


def get_neutral(def_type1: str, def_type2: str | None = None) -> list[str]:
    """Return types at neutral (1x) effectiveness against the defender.

    Args:
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.

    Returns:
        List of attacking types at 1x effectiveness.
    """
    return [atk_type for atk_type in TYPES if get_effectiveness(atk_type, def_type1, def_type2) == NEUTRAL_VALUE]


def generate_all_type_combinations() -> list[tuple[str, str | None]]:
    """Generate all 171 unique type combinations.

    Returns:
        List of 171 tuples:
        - 18 monotypes as (type, None)
        - 153 dual types as (type1, type2), normalized alphabetically
    """
    # 18 monotypes
    monotypes: list[tuple[str, str | None]] = [(t, None) for t in TYPES]

    # 153 dual types (alphabetically normalized to avoid duplicates)
    dual_types: list[tuple[str, str | None]] = [
        (type1, type2) if type1 < type2 else (type2, type1) for i, type1 in enumerate(TYPES) for type2 in TYPES[i + 1 :]
    ]

    combinations = monotypes + dual_types

    return combinations


def score_defensive_typing(
    def_type1: str,
    def_type2: str | None,
    attacking_types: list[str],
) -> dict[str, Any]:
    """Score defensive typing against a set of attacking types.

    Args:
        def_type1: The defender's primary type.
        def_type2: The defender's secondary type, or None for monotype.
        attacking_types: List of attacking types to evaluate against.

    Returns:
        Dictionary containing:
        - immunities: List of types the defender is immune to.
        - resistances: List of types the defender resists.
        - neutral: List of types with neutral effectiveness.
        - weaknesses: List of types the defender is weak to.
        - immunity_count: Count of immunities.
        - resistance_count: Count of resistances.
        - neutral_count: Count of neutral matchups.
        - weakness_count: Count of weaknesses.
    """
    immunities: list[str] = []
    resistances: list[str] = []
    neutral: list[str] = []
    weaknesses: list[str] = []

    for atk_type in attacking_types:
        effectiveness = get_effectiveness(atk_type, def_type1, def_type2)

        if effectiveness == 0.0:
            immunities.append(atk_type)
        elif effectiveness < 1.0:
            resistances.append(atk_type)
        elif effectiveness == 1.0:
            neutral.append(atk_type)
        else:  # effectiveness > 1.0
            weaknesses.append(atk_type)

    return {
        "immunities": immunities,
        "resistances": resistances,
        "neutral": neutral,
        "weaknesses": weaknesses,
        "immunity_count": len(immunities),
        "resistance_count": len(resistances),
        "neutral_count": len(neutral),
        "weakness_count": len(weaknesses),
    }
