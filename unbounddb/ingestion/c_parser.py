"""ABOUTME: Parser for C source files from Dynamic Pokemon Expansion.
ABOUTME: Extracts pokemon stats, learnsets, and other data from C structs."""

import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass
class PokemonStats:
    """Pokemon base stats parsed from Base_Stats.c."""

    species: str
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    type1: str
    type2: str
    ability1: str
    ability2: str
    hidden_ability: str
    catch_rate: int
    exp_yield: int
    egg_group1: str
    egg_group2: str


@dataclass
class LearnsetEntry:
    """Single learnset entry."""

    pokemon: str
    move: str
    level: int


def _clean_species_name(species: str) -> str:
    """Convert SPECIES_BULBASAUR to Bulbasaur."""
    name = species.replace("SPECIES_", "")
    # Handle special cases like SPECIES_NIDORAN_F
    return name.replace("_", " ").title()


def _clean_type_name(type_const: str) -> str:
    """Convert TYPE_GRASS to Grass."""
    return type_const.replace("TYPE_", "").title()


def _clean_ability_name(ability_const: str) -> str:
    """Convert ABILITY_OVERGROW to Overgrow."""
    name = ability_const.replace("ABILITY_", "")
    if name == "NONE":
        return ""
    return name.replace("_", " ").title()


def _clean_egg_group(egg_group: str) -> str:
    """Convert EGG_GROUP_MONSTER to Monster."""
    name = egg_group.replace("EGG_GROUP_", "")
    return name.replace("_", " ").title()


def _clean_move_name(move_const: str) -> str:
    """Convert MOVE_VINEWHIP to Vine Whip."""
    name = move_const.replace("MOVE_", "")
    # Insert space before capital letters for CamelCase names
    # But most moves are already uppercase, so just title case
    return name.replace("_", " ").title()


def parse_base_stats(content: str) -> list[PokemonStats]:
    """Parse Base_Stats.c content to extract pokemon stats.

    Args:
        content: Raw C file content.

    Returns:
        List of PokemonStats dataclasses.
    """
    pokemon_list = []

    # Pattern to match each pokemon block
    # [SPECIES_NAME] = { ... }
    species_pattern = re.compile(r"\[SPECIES_(\w+)\]\s*=\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL)

    # Patterns for individual fields
    field_patterns = {
        "baseHP": re.compile(r"\.baseHP\s*=\s*(\d+)"),
        "baseAttack": re.compile(r"\.baseAttack\s*=\s*(\d+)"),
        "baseDefense": re.compile(r"\.baseDefense\s*=\s*(\d+)"),
        "baseSpAttack": re.compile(r"\.baseSpAttack\s*=\s*(\d+)"),
        "baseSpDefense": re.compile(r"\.baseSpDefense\s*=\s*(\d+)"),
        "baseSpeed": re.compile(r"\.baseSpeed\s*=\s*(\d+)"),
        "type1": re.compile(r"\.type1\s*=\s*(TYPE_\w+)"),
        "type2": re.compile(r"\.type2\s*=\s*(TYPE_\w+)"),
        "ability1": re.compile(r"\.ability1\s*=\s*(ABILITY_\w+)"),
        "ability2": re.compile(r"\.ability2\s*=\s*(ABILITY_\w+)"),
        "hiddenAbility": re.compile(r"\.hiddenAbility\s*=\s*(ABILITY_\w+)"),
        "catchRate": re.compile(r"\.catchRate\s*=\s*(\d+)"),
        "expYield": re.compile(r"\.expYield\s*=\s*(\d+)"),
        "eggGroup1": re.compile(r"\.eggGroup1\s*=\s*(EGG_GROUP_\w+)"),
        "eggGroup2": re.compile(r"\.eggGroup2\s*=\s*(EGG_GROUP_\w+)"),
    }

    def get_int(block: str, field: str, default: int = 0) -> int:
        m = field_patterns[field].search(block)
        return int(m.group(1)) if m else default

    def get_str(block: str, field: str, default: str = "") -> str:
        m = field_patterns[field].search(block)
        return m.group(1) if m else default

    for match in species_pattern.finditer(content):
        species_name = match.group(1)
        block = match.group(2)

        # Skip NONE entry
        if species_name == "NONE":
            continue

        pokemon = PokemonStats(
            species=_clean_species_name(species_name),
            hp=get_int(block, "baseHP"),
            attack=get_int(block, "baseAttack"),
            defense=get_int(block, "baseDefense"),
            sp_attack=get_int(block, "baseSpAttack"),
            sp_defense=get_int(block, "baseSpDefense"),
            speed=get_int(block, "baseSpeed"),
            type1=_clean_type_name(get_str(block, "type1", "TYPE_NORMAL")),
            type2=_clean_type_name(get_str(block, "type2", "TYPE_NORMAL")),
            ability1=_clean_ability_name(get_str(block, "ability1", "ABILITY_NONE")),
            ability2=_clean_ability_name(get_str(block, "ability2", "ABILITY_NONE")),
            hidden_ability=_clean_ability_name(get_str(block, "hiddenAbility", "ABILITY_NONE")),
            catch_rate=get_int(block, "catchRate"),
            exp_yield=get_int(block, "expYield"),
            egg_group1=_clean_egg_group(get_str(block, "eggGroup1", "EGG_GROUP_UNDISCOVERED")),
            egg_group2=_clean_egg_group(get_str(block, "eggGroup2", "EGG_GROUP_UNDISCOVERED")),
        )
        pokemon_list.append(pokemon)

    return pokemon_list


def parse_learnsets(content: str) -> list[LearnsetEntry]:
    """Parse Learnsets.c content to extract move learnsets.

    Args:
        content: Raw C file content.

    Returns:
        List of LearnsetEntry dataclasses.
    """
    entries = []

    # Pattern to match learnset arrays
    # static const struct LevelUpMove sBulbasaurLevelUpLearnset[] = { ... };
    learnset_pattern = re.compile(
        r"static const struct LevelUpMove s(\w+)LevelUpLearnset\[\]\s*=\s*\{([^;]+)\};",
        re.MULTILINE | re.DOTALL,
    )

    # Pattern to match individual moves
    move_pattern = re.compile(r"LEVEL_UP_MOVE\s*\(\s*(\d+)\s*,\s*(MOVE_\w+)\s*\)")

    for match in learnset_pattern.finditer(content):
        pokemon_name = match.group(1)
        moves_block = match.group(2)

        # Skip Empty moveset
        if pokemon_name == "Empty":
            continue

        # Clean pokemon name (sBulbasaur -> Bulbasaur)
        clean_pokemon = pokemon_name.replace("_", " ").title()

        for move_match in move_pattern.finditer(moves_block):
            level = int(move_match.group(1))
            move = _clean_move_name(move_match.group(2))

            entries.append(
                LearnsetEntry(
                    pokemon=clean_pokemon,
                    move=move,
                    level=level,
                )
            )

    return entries


def base_stats_to_dataframe(stats: list[PokemonStats]) -> pl.DataFrame:
    """Convert list of PokemonStats to a Polars DataFrame.

    Args:
        stats: List of PokemonStats dataclasses.

    Returns:
        Polars DataFrame with pokemon stats.
    """
    data = {
        "name": [s.species for s in stats],
        "hp": [s.hp for s in stats],
        "attack": [s.attack for s in stats],
        "defense": [s.defense for s in stats],
        "sp_attack": [s.sp_attack for s in stats],
        "sp_defense": [s.sp_defense for s in stats],
        "speed": [s.speed for s in stats],
        "bst": [s.hp + s.attack + s.defense + s.sp_attack + s.sp_defense + s.speed for s in stats],
        "type1": [s.type1 for s in stats],
        "type2": [s.type2 for s in stats],
        "ability1": [s.ability1 for s in stats],
        "ability2": [s.ability2 for s in stats],
        "hidden_ability": [s.hidden_ability for s in stats],
        "catch_rate": [s.catch_rate for s in stats],
        "exp_yield": [s.exp_yield for s in stats],
        "egg_group1": [s.egg_group1 for s in stats],
        "egg_group2": [s.egg_group2 for s in stats],
    }
    return pl.DataFrame(data)


def learnsets_to_dataframe(entries: list[LearnsetEntry]) -> pl.DataFrame:
    """Convert list of LearnsetEntry to a Polars DataFrame.

    Args:
        entries: List of LearnsetEntry dataclasses.

    Returns:
        Polars DataFrame with learnset data.
    """
    data = {
        "pokemon": [e.pokemon for e in entries],
        "move": [e.move for e in entries],
        "level": [e.level for e in entries],
    }
    return pl.DataFrame(data)


def parse_base_stats_file(path: Path) -> pl.DataFrame:
    """Parse Base_Stats.c file to DataFrame.

    Args:
        path: Path to Base_Stats.c file.

    Returns:
        Polars DataFrame with pokemon stats.
    """
    content = path.read_text()
    stats = parse_base_stats(content)
    return base_stats_to_dataframe(stats)


def parse_learnsets_file(path: Path) -> pl.DataFrame:
    """Parse Learnsets.c file to DataFrame.

    Args:
        path: Path to Learnsets.c file.

    Returns:
        Polars DataFrame with learnset data.
    """
    content = path.read_text()
    entries = parse_learnsets(content)
    return learnsets_to_dataframe(entries)
