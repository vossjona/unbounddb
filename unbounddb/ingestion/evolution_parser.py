"""ABOUTME: Parses Evolution Table.c to extract Pokemon evolution data.
ABOUTME: Handles evolution methods, conditions, and filters out reverse evolutions."""

import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

# Regex to match species evolution blocks: [SPECIES_NAME] = {...},
# Uses non-greedy match and looks for },\n pattern to end blocks
SPECIES_BLOCK_PATTERN = re.compile(
    r"\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\},?\s*(?=\[SPECIES_|\Z)",
    re.MULTILINE | re.DOTALL,
)

# Regex to match individual evolution entries: {EVO_METHOD, PARAM1, SPECIES_TARGET, PARAM2}
EVOLUTION_ENTRY_PATTERN = re.compile(r"\{(EVO_\w+)\s*,\s*([^,]+)\s*,\s*SPECIES_(\w+)\s*,\s*([^}]+)\}")

# Evolution method mapping (collapse day/night variants per user request)
EVO_METHOD_MAP: dict[str, str] = {
    "EVO_LEVEL": "Level",
    "EVO_LEVEL_DAY": "Level",
    "EVO_LEVEL_NIGHT": "Level",
    "EVO_LEVEL_DUSK": "Level",
    "EVO_LEVEL_ATK_GT_DEF": "Level (Atk > Def)",
    "EVO_LEVEL_ATK_EQ_DEF": "Level (Atk = Def)",
    "EVO_LEVEL_ATK_LT_DEF": "Level (Atk < Def)",
    "EVO_LEVEL_MALE": "Level (Male)",
    "EVO_LEVEL_FEMALE": "Level (Female)",
    "EVO_LEVEL_SILCOON": "Level (Silcoon)",
    "EVO_LEVEL_CASCOON": "Level (Cascoon)",
    "EVO_LEVEL_NINJASK": "Level (Ninjask)",
    "EVO_LEVEL_SHEDINJA": "Level (Shedinja)",
    "EVO_LEVEL_RAIN": "Level (Rain)",
    "EVO_LEVEL_DARK_TYPE_MON_IN_PARTY": "Level (Dark in Party)",
    "EVO_LEVEL_NATURE_LOW_KEY": "Level (Low Key Nature)",
    "EVO_LEVEL_NATURE_AMPED": "Level (Amped Nature)",
    "EVO_ITEM": "Stone",
    "EVO_ITEM_HOLD": "Held Item",
    "EVO_ITEM_HOLD_DAY": "Held Item",
    "EVO_ITEM_HOLD_NIGHT": "Held Item",
    "EVO_ITEM_MALE": "Stone (Male)",
    "EVO_ITEM_FEMALE": "Stone (Female)",
    "EVO_TRADE": "Trade",
    "EVO_TRADE_ITEM": "Trade",
    "EVO_TRADE_SPECIFIC_MON": "Trade",
    "EVO_FRIENDSHIP": "Friendship",
    "EVO_FRIENDSHIP_DAY": "Friendship",
    "EVO_FRIENDSHIP_NIGHT": "Friendship",
    "EVO_FRIENDSHIP_MOVE_TYPE": "Friendship (Move Type)",
    "EVO_MOVE": "Move",
    "EVO_MOVE_TYPE": "Move Type",
    "EVO_MOVE_TWO_SEGMENT": "Move (Two Segment)",
    "EVO_MOVE_THREE_SEGMENT": "Move (Three Segment)",
    "EVO_MAP": "Location",
    "EVO_MAPSEC": "Location",
    "EVO_MEGA_EVOLUTION": "Mega",
    "EVO_PRIMAL_REVERSION": "Primal",
    "EVO_GIGANTAMAX": "Gigantamax",
    "EVO_HOLD_ITEM_DAY": "Held Item",
    "EVO_HOLD_ITEM_NIGHT": "Held Item",
    "EVO_OTHER_PARTY_MON": "Party Pokemon",
    "EVO_SPECIFIC_MON_IN_PARTY": "Party Pokemon",
    "EVO_BEAUTY": "Beauty",
    "EVO_SPECIFIC_MAP": "Location",
    "EVO_SPECIFIC_MAPSEC": "Location",
    "EVO_CRITICAL_HITS": "Critical Hits",
    "EVO_SCRIPT_TRIGGER_DMG": "Script Trigger",
    "EVO_DARK_SCROLL": "Dark Scroll",
    "EVO_WATER_SCROLL": "Water Scroll",
    "EVO_RECOIL_DAMAGE_MALE": "Recoil (Male)",
    "EVO_RECOIL_DAMAGE_FEMALE": "Recoil (Female)",
    "EVO_NONE": "None",
}


@dataclass
class EvolutionEntry:
    """Represents a single Pokemon evolution."""

    from_pokemon: str
    to_pokemon: str
    method: str
    condition: str


def _clean_species_name(species: str) -> str:
    """Convert SPECIES_NAME to readable name.

    Args:
        species: Species name like BULBASAUR or CHARIZARD_MEGA_X.

    Returns:
        Cleaned name like Bulbasaur or Charizard Mega X.
    """
    # Replace underscores with spaces, then title case
    return species.replace("_", " ").title()


def _is_reverse_evolution(from_species: str, to_species: str, method: str, param1: str) -> bool:
    """Check if this is a reverse evolution (mega->base) that should be skipped.

    Args:
        from_species: Source species (e.g., CHARIZARD_MEGA_X).
        to_species: Target species (e.g., CHARIZARD).
        method: Evolution method (e.g., EVO_MEGA_EVOLUTION).
        param1: First parameter (may contain ITEM_NONE).

    Returns:
        True if this is a reverse evolution that should be skipped.
    """
    from_is_special = "_MEGA" in from_species or "_GIGA" in from_species or "_PRIMAL" in from_species
    to_is_special = "_MEGA" in to_species or "_GIGA" in to_species or "_PRIMAL" in to_species

    # Skip if going from special form to base form
    if from_is_special and not to_is_special:
        return True

    # Skip mega evolutions with ITEM_NONE (reverse mega)
    return method == "EVO_MEGA_EVOLUTION" and "ITEM_NONE" in param1


def _clean_item_name(item: str) -> str:
    """Convert ITEM_NAME to readable item name.

    Args:
        item: Item constant like ITEM_FIRE_STONE or ITEM_CHARIZARDITE_X.

    Returns:
        Cleaned name like Fire Stone or Charizardite X.
    """
    if item.startswith("ITEM_"):
        item = item[5:]  # Remove ITEM_ prefix
    return item.replace("_", " ").title()


def _clean_move_name(move: str) -> str:
    """Convert MOVE_NAME to readable move name.

    Args:
        move: Move constant like MOVE_ROLLOUT.

    Returns:
        Cleaned name like Rollout.
    """
    if move.startswith("MOVE_"):
        move = move[5:]  # Remove MOVE_ prefix
    return move.replace("_", " ").title()


def _clean_type_name(type_const: str) -> str:
    """Convert TYPE_NAME to readable type name.

    Args:
        type_const: Type constant like TYPE_FAIRY.

    Returns:
        Cleaned name like Fairy.
    """
    if type_const.startswith("TYPE_"):
        type_const = type_const[5:]  # Remove TYPE_ prefix
    return type_const.title()


def _clean_species_param(param: str) -> str:
    """Clean species parameter for conditions."""
    return _clean_species_name(param.replace("SPECIES_", ""))


# Condition builders for different method categories
_ITEM_METHODS = frozenset(
    {
        "EVO_ITEM",
        "EVO_ITEM_MALE",
        "EVO_ITEM_FEMALE",
        "EVO_ITEM_HOLD",
        "EVO_ITEM_HOLD_DAY",
        "EVO_ITEM_HOLD_NIGHT",
        "EVO_HOLD_ITEM_DAY",
        "EVO_HOLD_ITEM_NIGHT",
        "EVO_TRADE_ITEM",
        "EVO_MEGA_EVOLUTION",
        "EVO_PRIMAL_REVERSION",
    }
)

_MOVE_TYPE_METHODS = frozenset({"EVO_MOVE_TYPE", "EVO_FRIENDSHIP_MOVE_TYPE"})

_SPECIES_METHODS = frozenset({"EVO_TRADE_SPECIFIC_MON", "EVO_OTHER_PARTY_MON", "EVO_SPECIFIC_MON_IN_PARTY"})

_PASSTHROUGH_METHODS = frozenset(
    {
        "EVO_BEAUTY",
        "EVO_CRITICAL_HITS",
        "EVO_RECOIL_DAMAGE_MALE",
        "EVO_RECOIL_DAMAGE_FEMALE",
    }
)


def _build_condition(method: str, param1: str, param2: str) -> str:  # noqa: PLR0911
    """Build human-readable condition from method and parameters.

    Args:
        method: Evolution method constant.
        param1: First parameter (level, item, move, etc.).
        param2: Second parameter (usually unused or item).

    Returns:
        Condition string like "16", "Fire Stone", "Rollout", or empty.
    """
    param1 = param1.strip()

    # Level-based evolutions: param1 is the level number
    if method.startswith("EVO_LEVEL"):
        try:
            return str(int(param1))
        except ValueError:
            return param1

    # Item-based evolutions (stones, held items, mega stones, orbs)
    if method in _ITEM_METHODS:
        return _clean_item_name(param1)

    # Move-based evolutions
    if method == "EVO_MOVE":
        return _clean_move_name(param1)

    # Move type evolutions
    if method in _MOVE_TYPE_METHODS:
        return _clean_type_name(param1)

    # Species-based conditions (trade with Pokemon, party Pokemon)
    if method in _SPECIES_METHODS:
        return _clean_species_param(param1)

    # Passthrough methods (beauty, critical hits, recoil damage)
    if method in _PASSTHROUGH_METHODS:
        return param1

    # Default: return empty for friendship, trade without item, etc.
    return ""


def parse_evolutions(content: str) -> list[EvolutionEntry]:
    """Parse Evolution Table.c content into evolution entries.

    Args:
        content: Raw content from Evolution Table.c file.

    Returns:
        List of EvolutionEntry objects.
    """
    entries: list[EvolutionEntry] = []

    # Find all species blocks
    for species_match in SPECIES_BLOCK_PATTERN.finditer(content):
        from_species = species_match.group(1)
        block_content = species_match.group(2)

        # Skip species blocks that are just placeholders
        if from_species in ("NONE", "EGG"):
            continue

        # Find all evolution entries in this block
        for evo_match in EVOLUTION_ENTRY_PATTERN.finditer(block_content):
            method = evo_match.group(1)
            param1 = evo_match.group(2)
            to_species = evo_match.group(3)
            param2 = evo_match.group(4)

            # Skip EVO_NONE entries
            if method == "EVO_NONE":
                continue

            # Skip reverse evolutions
            if _is_reverse_evolution(from_species, to_species, method, param1):
                continue

            # Map method to human-readable form
            method_clean = EVO_METHOD_MAP.get(method, method)

            # Build condition
            condition = _build_condition(method, param1, param2)

            entries.append(
                EvolutionEntry(
                    from_pokemon=_clean_species_name(from_species),
                    to_pokemon=_clean_species_name(to_species),
                    method=method_clean,
                    condition=condition,
                )
            )

    return entries


def parse_evolutions_file(path: Path) -> pl.DataFrame:
    """Parse Evolution Table.c file to DataFrame.

    Args:
        path: Path to Evolution Table.c file.

    Returns:
        DataFrame with columns: from_pokemon, to_pokemon, method, condition,
        from_pokemon_key, to_pokemon_key.
    """
    # Import here to avoid circular import with build module
    from unbounddb.build.normalize import slugify  # noqa: PLC0415

    content = path.read_text(encoding="utf-8")
    entries = parse_evolutions(content)

    if not entries:
        # Return empty DataFrame with correct schema
        return pl.DataFrame(
            schema={
                "from_pokemon": pl.String,
                "to_pokemon": pl.String,
                "method": pl.String,
                "condition": pl.String,
                "from_pokemon_key": pl.String,
                "to_pokemon_key": pl.String,
            }
        )

    df = pl.DataFrame(
        {
            "from_pokemon": [e.from_pokemon for e in entries],
            "to_pokemon": [e.to_pokemon for e in entries],
            "method": [e.method for e in entries],
            "condition": [e.condition for e in entries],
        }
    )

    # Add slugified keys for joining
    df = df.with_columns(
        [
            pl.col("from_pokemon").map_elements(slugify, return_dtype=pl.String).alias("from_pokemon_key"),
            pl.col("to_pokemon").map_elements(slugify, return_dtype=pl.String).alias("to_pokemon_key"),
        ]
    )

    return df
