"""ABOUTME: Parser for Showdown/PokePaste format trainer battle data.
ABOUTME: Extracts trainer Pokemon teams with EVs, moves, items, and abilities."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from unbounddb.build.normalize import slugify

# Regex patterns for parsing Showdown format
# First line: "Trainer Name - Difficulty (Pokemon) @ Item" or "Trainer Name (Pokemon) @ Item"
HEADER_PATTERN = re.compile(r"^(.+?)\s*(?:-\s*(Insane|Expert|Difficult|Easy))?\s*\(([^)]+)\)\s*(?:@\s*(.*))?$")

# Level: "Level: 19"
LEVEL_PATTERN = re.compile(r"^Level:\s*(\d+)$")

# Nature: "Bold Nature"
NATURE_PATTERN = re.compile(r"^(\w+)\s+Nature$")

# Ability: "Ability: Flower Veil"
ABILITY_PATTERN = re.compile(r"^Ability:\s*(.+)$")

# EVs: "EVs: 252 HP / 252 Def / 4 SpD"
EVS_PATTERN = re.compile(r"^EVs:\s*(.+)$")

# Move: "- Moonblast"
MOVE_PATTERN = re.compile(r"^-\s*(.+)$")

# EV stat mapping
EV_STAT_MAP = {
    "hp": "hp",
    "atk": "attack",
    "attack": "attack",
    "def": "defense",
    "defense": "defense",
    "spa": "sp_attack",
    "spatk": "sp_attack",
    "sp. atk": "sp_attack",
    "spd": "sp_defense",
    "spdef": "sp_defense",
    "sp. def": "sp_defense",
    "spe": "speed",
    "speed": "speed",
}


@dataclass
class TrainerPokemon:
    """Single Pokemon from a trainer's team in Showdown format."""

    trainer_name: str
    difficulty: str | None
    pokemon: str
    held_item: str | None
    level: int
    nature: str
    ability: str
    evs: dict[str, int] = field(default_factory=dict)
    moves: list[str] = field(default_factory=list)


def _parse_evs(evs_str: str) -> dict[str, int]:
    """Parse EVs string into a dictionary.

    Args:
        evs_str: EV string like "252 HP / 252 Def / 4 SpD"

    Returns:
        Dictionary mapping stat names to EV values.
    """
    result: dict[str, int] = {
        "hp": 0,
        "attack": 0,
        "defense": 0,
        "sp_attack": 0,
        "sp_defense": 0,
        "speed": 0,
    }

    parts = evs_str.split("/")
    for part in parts:
        stripped_part = part.strip()
        # Match "252 HP" or "4 SpD"
        match = re.match(r"(\d+)\s+(.+)", stripped_part)
        if match:
            value = int(match.group(1))
            stat_name = match.group(2).strip().lower()

            # Map to standard stat name
            if stat_name in EV_STAT_MAP:
                result[EV_STAT_MAP[stat_name]] = value

    return result


def get_battle_group(trainer_name: str, difficulty: str | None) -> str:
    """Generate battle group identifier for double battle matching.

    Args:
        trainer_name: Full trainer name, may contain "w/" for partners.
        difficulty: Difficulty level like "Insane", "Expert", etc.

    Returns:
        Slugified battle group identifier.
    """
    # If this is a partner, extract the base trainer name after "w/"
    base = trainer_name.split(" w/ ")[1] if " w/ " in trainer_name else trainer_name

    suffix = f"_{difficulty.lower()}" if difficulty else ""
    return slugify(base) + suffix


def is_double_battle(trainer_name: str) -> bool:
    """Check if a trainer name indicates a double battle partner.

    Args:
        trainer_name: Full trainer name.

    Returns:
        True if this is a double battle entry.
    """
    return " w/ " in trainer_name


@dataclass
class _ParsedFields:
    """Intermediate container for parsed line fields."""

    level: int = 0
    nature: str = ""
    ability: str = ""
    evs: dict[str, int] = field(
        default_factory=lambda: {
            "hp": 0,
            "attack": 0,
            "defense": 0,
            "sp_attack": 0,
            "sp_defense": 0,
            "speed": 0,
        }
    )
    moves: list[str] = field(default_factory=list)


def _parse_line_fields(lines: list[str]) -> _ParsedFields:
    """Parse field lines (everything after header) into a ParsedFields object.

    Args:
        lines: List of lines after the header line.

    Returns:
        ParsedFields with extracted data.
    """
    result = _ParsedFields()

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if match := LEVEL_PATTERN.match(stripped_line):
            result.level = int(match.group(1))
        elif match := NATURE_PATTERN.match(stripped_line):
            result.nature = match.group(1)
        elif match := ABILITY_PATTERN.match(stripped_line):
            result.ability = match.group(1).strip()
        elif match := EVS_PATTERN.match(stripped_line):
            result.evs = _parse_evs(match.group(1))
        elif match := MOVE_PATTERN.match(stripped_line):
            move = match.group(1).strip()
            if move and move != "-":
                result.moves.append(move)

    return result


def parse_showdown_entry(lines: list[str]) -> TrainerPokemon | None:
    """Parse a single Pokemon entry from Showdown format lines.

    Args:
        lines: List of lines for one Pokemon entry.

    Returns:
        TrainerPokemon dataclass or None if parsing fails.
    """
    if not lines:
        return None

    # Parse header line
    header_match = HEADER_PATTERN.match(lines[0].strip())
    if not header_match:
        return None

    trainer_name = header_match.group(1).strip()
    difficulty = header_match.group(2)  # May be None
    pokemon = header_match.group(3).strip()
    held_item = header_match.group(4).strip() if header_match.group(4) else None

    # Parse remaining lines
    fields = _parse_line_fields(lines[1:])

    return TrainerPokemon(
        trainer_name=trainer_name,
        difficulty=difficulty,
        pokemon=pokemon,
        held_item=held_item,
        level=fields.level,
        nature=fields.nature,
        ability=fields.ability,
        evs=fields.evs,
        moves=fields.moves,
    )


def parse_showdown_file(content: str) -> list[TrainerPokemon]:
    """Parse entire Showdown format file content.

    Args:
        content: Full file content in Showdown/PokePaste format.

    Returns:
        List of TrainerPokemon dataclasses.
    """
    entries: list[TrainerPokemon] = []
    current_lines: list[str] = []

    for line in content.split("\n"):
        # Check if this is a new entry (starts with trainer header)
        if HEADER_PATTERN.match(line.strip()):
            # Parse previous entry if exists
            if current_lines and (entry := parse_showdown_entry(current_lines)):
                entries.append(entry)
            current_lines = [line]
        elif line.strip():
            # Add non-empty lines to current entry
            current_lines.append(line)

    # Don't forget the last entry
    if current_lines and (entry := parse_showdown_entry(current_lines)):
        entries.append(entry)

    return entries


def entries_to_dataframes(
    entries: list[TrainerPokemon],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Convert parsed entries to three normalized DataFrames.

    Args:
        entries: List of TrainerPokemon dataclasses.

    Returns:
        Tuple of (trainers_df, trainer_pokemon_df, trainer_pokemon_moves_df).
    """
    # Build trainer lookup: (name, difficulty) -> trainer_id
    trainer_lookup: dict[tuple[str, str | None], int] = {}
    trainers_data: list[dict[str, int | str | bool | None]] = []

    for entry in entries:
        key = (entry.trainer_name, entry.difficulty)
        if key not in trainer_lookup:
            trainer_id = len(trainer_lookup) + 1
            trainer_lookup[key] = trainer_id

            battle_group = get_battle_group(entry.trainer_name, entry.difficulty)
            is_double = is_double_battle(entry.trainer_name)

            trainers_data.append(
                {
                    "trainer_id": trainer_id,
                    "name": entry.trainer_name,
                    "difficulty": entry.difficulty,
                    "battle_group": battle_group,
                    "is_double_battle": is_double,
                }
            )

    # Build trainer_pokemon and trainer_pokemon_moves
    trainer_pokemon_data: list[dict[str, int | str | None]] = []
    trainer_pokemon_moves_data: list[dict[str, int | str]] = []

    # Track slot per trainer
    trainer_slots: dict[int, int] = {}

    for pokemon_id, entry in enumerate(entries, start=1):
        trainer_id = trainer_lookup[(entry.trainer_name, entry.difficulty)]

        # Increment slot for this trainer
        if trainer_id not in trainer_slots:
            trainer_slots[trainer_id] = 0
        trainer_slots[trainer_id] += 1
        slot = trainer_slots[trainer_id]

        pokemon_key = slugify(entry.pokemon)

        trainer_pokemon_data.append(
            {
                "id": pokemon_id,
                "trainer_id": trainer_id,
                "pokemon_key": pokemon_key,
                "slot": slot,
                "level": entry.level,
                "ability": entry.ability,
                "held_item": entry.held_item,
                "nature": entry.nature,
                "ev_hp": entry.evs.get("hp", 0),
                "ev_attack": entry.evs.get("attack", 0),
                "ev_defense": entry.evs.get("defense", 0),
                "ev_sp_attack": entry.evs.get("sp_attack", 0),
                "ev_sp_defense": entry.evs.get("sp_defense", 0),
                "ev_speed": entry.evs.get("speed", 0),
            }
        )

        # Add moves
        for move_slot, move in enumerate(entry.moves, start=1):
            move_key = slugify(move)
            trainer_pokemon_moves_data.append(
                {
                    "trainer_pokemon_id": pokemon_id,
                    "move_key": move_key,
                    "slot": move_slot,
                }
            )

    # Create DataFrames
    trainers_df = pl.DataFrame(trainers_data)
    trainer_pokemon_df = pl.DataFrame(trainer_pokemon_data)
    trainer_pokemon_moves_df = pl.DataFrame(trainer_pokemon_moves_data)

    return trainers_df, trainer_pokemon_df, trainer_pokemon_moves_df


def parse_showdown_file_to_dataframes(
    path: Path,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Parse Showdown format file directly to DataFrames.

    Args:
        path: Path to the Showdown/PokePaste format file.

    Returns:
        Tuple of (trainers_df, trainer_pokemon_df, trainer_pokemon_moves_df).
    """
    content = path.read_text(encoding="utf-8")
    entries = parse_showdown_file(content)
    return entries_to_dataframes(entries)
