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


@dataclass
class MoveInfo:
    """Move information parsed from moves_info.h."""

    name: str
    type_name: str
    category: str
    power: int
    accuracy: int
    pp: int
    priority: int
    effect: str
    has_secondary_effect: bool
    makes_contact: bool
    is_sound_move: bool
    is_punch_move: bool
    is_bite_move: bool
    is_pulse_move: bool


def _clean_move_type(type_const: str) -> str:
    """Convert TYPE_FIRE to Fire.

    Args:
        type_const: Type constant from C source.

    Returns:
        Human-readable type name.
    """
    return type_const.replace("TYPE_", "").title()


def _clean_category(category: str) -> str:
    """Convert DAMAGE_CATEGORY_PHYSICAL to Physical.

    Args:
        category: Category constant from C source.

    Returns:
        Human-readable category name.
    """
    mapping = {
        "DAMAGE_CATEGORY_PHYSICAL": "Physical",
        "DAMAGE_CATEGORY_SPECIAL": "Special",
        "DAMAGE_CATEGORY_STATUS": "Status",
    }
    return mapping.get(category, category)


def parse_moves_info(content: str) -> list[MoveInfo]:
    """Parse moves_info.h content to extract move data.

    Args:
        content: Raw C file content.

    Returns:
        List of MoveInfo dataclasses.
    """
    moves_list = []

    # Pattern to match move blocks: [MOVE_NAME] = { ... },
    # Must handle nested braces from additionalEffects
    move_pattern = re.compile(
        r"\[MOVE_(\w+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
        re.MULTILINE | re.DOTALL,
    )

    # Field patterns
    # Handle Gen 6+ conditional: B_UPDATED_MOVE_DATA >= GEN_6 ? 90 : 95
    name_pattern = re.compile(r'\.name\s*=\s*COMPOUND_STRING\s*\(\s*"([^"]+)"')
    type_pattern = re.compile(r"\.type\s*=\s*(TYPE_\w+)")
    category_pattern = re.compile(r"\.category\s*=\s*(DAMAGE_CATEGORY_\w+)")
    power_pattern = re.compile(r"\.power\s*=\s*(?:B_UPDATED_MOVE_DATA\s*>=\s*GEN_\d+\s*\?\s*)?(\d+)")
    accuracy_pattern = re.compile(r"\.accuracy\s*=\s*(?:B_UPDATED_MOVE_DATA\s*>=\s*GEN_\d+\s*\?\s*)?(\d+)")
    pp_pattern = re.compile(r"\.pp\s*=\s*(?:B_UPDATED_MOVE_DATA\s*>=\s*GEN_\d+\s*\?\s*)?(\d+)")
    priority_pattern = re.compile(r"\.priority\s*=\s*(-?\d+)")
    effect_pattern = re.compile(r"\.effect\s*=\s*(EFFECT_\w+)")

    # Boolean flag patterns
    makes_contact_pattern = re.compile(r"\.makesContact\s*=\s*TRUE")
    sound_move_pattern = re.compile(r"\.soundMove\s*=\s*TRUE")
    punch_move_pattern = re.compile(r"\.punchingMove\s*=\s*TRUE")
    bite_move_pattern = re.compile(r"\.bitingMove\s*=\s*TRUE")
    pulse_move_pattern = re.compile(r"\.pulseMove\s*=\s*TRUE")

    # Secondary effect detection
    has_secondary_pattern = re.compile(r"\.additionalEffects\s*=")

    for match in move_pattern.finditer(content):
        move_const = match.group(1)
        block = match.group(2)

        # Skip NONE entry
        if move_const == "NONE":
            continue

        # Extract name from COMPOUND_STRING
        name_match = name_pattern.search(block)
        if not name_match:
            continue  # Skip moves without proper name
        name = name_match.group(1)

        # Extract other fields with defaults
        type_match = type_pattern.search(block)
        type_name = _clean_move_type(type_match.group(1)) if type_match else "Normal"

        category_match = category_pattern.search(block)
        category = _clean_category(category_match.group(1)) if category_match else "Status"

        power_match = power_pattern.search(block)
        power = int(power_match.group(1)) if power_match else 0

        accuracy_match = accuracy_pattern.search(block)
        accuracy = int(accuracy_match.group(1)) if accuracy_match else 0

        pp_match = pp_pattern.search(block)
        pp = int(pp_match.group(1)) if pp_match else 0

        priority_match = priority_pattern.search(block)
        priority = int(priority_match.group(1)) if priority_match else 0

        effect_match = effect_pattern.search(block)
        effect = effect_match.group(1) if effect_match else "EFFECT_HIT"

        # Boolean flags
        makes_contact = bool(makes_contact_pattern.search(block))
        is_sound_move = bool(sound_move_pattern.search(block))
        is_punch_move = bool(punch_move_pattern.search(block))
        is_bite_move = bool(bite_move_pattern.search(block))
        is_pulse_move = bool(pulse_move_pattern.search(block))
        has_secondary_effect = bool(has_secondary_pattern.search(block))

        move = MoveInfo(
            name=name,
            type_name=type_name,
            category=category,
            power=power,
            accuracy=accuracy,
            pp=pp,
            priority=priority,
            effect=effect,
            has_secondary_effect=has_secondary_effect,
            makes_contact=makes_contact,
            is_sound_move=is_sound_move,
            is_punch_move=is_punch_move,
            is_bite_move=is_bite_move,
            is_pulse_move=is_pulse_move,
        )
        moves_list.append(move)

    return moves_list


def moves_info_to_dataframe(moves: list[MoveInfo]) -> pl.DataFrame:
    """Convert list of MoveInfo to a Polars DataFrame.

    Args:
        moves: List of MoveInfo dataclasses.

    Returns:
        Polars DataFrame with move data.
    """
    data = {
        "name": [m.name for m in moves],
        "type": [m.type_name for m in moves],
        "category": [m.category for m in moves],
        "power": [m.power for m in moves],
        "accuracy": [m.accuracy for m in moves],
        "pp": [m.pp for m in moves],
        "priority": [m.priority for m in moves],
        "effect": [m.effect for m in moves],
        "has_secondary_effect": [m.has_secondary_effect for m in moves],
        "makes_contact": [m.makes_contact for m in moves],
        "is_sound_move": [m.is_sound_move for m in moves],
        "is_punch_move": [m.is_punch_move for m in moves],
        "is_bite_move": [m.is_bite_move for m in moves],
        "is_pulse_move": [m.is_pulse_move for m in moves],
    }
    return pl.DataFrame(data)


def parse_moves_info_file(path: Path) -> pl.DataFrame:
    """Parse moves_info.h file to DataFrame.

    Args:
        path: Path to moves_info.h file.

    Returns:
        Polars DataFrame with move data.
    """
    content = path.read_text()
    moves = parse_moves_info(content)
    return moves_info_to_dataframe(moves)
