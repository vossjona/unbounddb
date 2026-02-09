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


def _is_partner_entry(trainer_name: str) -> bool:
    """Check if a trainer name is a double battle partner entry.

    Partner entries have "w/" *outside* of bracket notation.
    E.g. "Shadow Grunt w/ Marlon 1" is a partner, but
    "Crystal Peak [Hoopa w/ Rayquaza]" is NOT (w/ is inside brackets).

    Args:
        trainer_name: Full trainer name.

    Returns:
        True if this is a partner entry whose Pokemon should be merged.
    """
    if " w/ " not in trainer_name:
        return False
    # If "w/" appears inside brackets like "[Hoopa w/ Rayquaza]", it's not a partner
    bracket_pos = trainer_name.find("[")
    w_pos = trainer_name.find(" w/ ")
    return bracket_pos == -1 or w_pos < bracket_pos


def _extract_partner_base(trainer_name: str) -> str:
    """Extract the base trainer name from a partner entry.

    "Shadow Grunt w/ Marlon 1" -> "Marlon 1"

    Args:
        trainer_name: Partner trainer name containing " w/ ".

    Returns:
        The base trainer name after " w/ ".
    """
    return trainer_name.split(" w/ ")[1]


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


def _find_main_battle_for_partner(
    partner_name: str,
    difficulty: str | None,
    battle_lookup: dict[tuple[str, str | None], int],
) -> int | None:
    """Find the main battle ID for a double battle partner.

    Searches for a main trainer whose name ends with the part after "w/".
    E.g., partner "Shadow Grunt w/ Marlon 1" matches "Shadow Admin Marlon 1".

    Args:
        partner_name: The partner trainer name (contains " w/ ").
        difficulty: Difficulty level to match.
        battle_lookup: Existing (name, difficulty) -> battle_id mapping.

    Returns:
        The battle_id of the matching main trainer, or None if not found.
    """
    base = _extract_partner_base(partner_name)
    for (name, diff), battle_id in battle_lookup.items():
        if diff == difficulty and name.endswith(base) and name != partner_name:
            return battle_id
    return None


def entries_to_dataframes(
    entries: list[TrainerPokemon],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Convert parsed entries to three normalized DataFrames.

    Double battle partners (entries with "w/" outside brackets) are merged
    into their main battle entry. Their Pokemon get sequential slot numbers
    continuing after the main trainer's team.

    After building individual battles, combined "Elite Four + Champion"
    entries are added per difficulty, grouping all E4 and Champion Pokemon.

    Args:
        entries: List of TrainerPokemon dataclasses.

    Returns:
        Tuple of (battles_df, battle_pokemon_df, battle_pokemon_moves_df).
    """
    # First pass: build battle lookup, skipping partner entries
    battle_lookup: dict[tuple[str, str | None], int] = {}
    battles_data: list[dict[str, int | str | None]] = []

    for entry in entries:
        key = (entry.trainer_name, entry.difficulty)
        if key in battle_lookup:
            continue
        if _is_partner_entry(entry.trainer_name):
            continue

        battle_id = len(battle_lookup) + 1
        battle_lookup[key] = battle_id
        battles_data.append(
            {
                "battle_id": battle_id,
                "name": entry.trainer_name,
                "difficulty": entry.difficulty,
            }
        )

    # Second pass: build battle_pokemon and battle_pokemon_moves
    battle_pokemon_data: list[dict[str, int | str | None]] = []
    battle_pokemon_moves_data: list[dict[str, int | str]] = []

    # Track slot per battle
    battle_slots: dict[int, int] = {}
    pokemon_id_counter = 0

    for entry in entries:
        # Determine which battle this entry belongs to
        if _is_partner_entry(entry.trainer_name):
            matched_id = _find_main_battle_for_partner(entry.trainer_name, entry.difficulty, battle_lookup)
            if matched_id is not None:
                battle_id = matched_id
            else:
                # No matching main trainer found — treat as standalone battle
                key = (entry.trainer_name, entry.difficulty)
                if key not in battle_lookup:
                    battle_id = len(battle_lookup) + 1
                    battle_lookup[key] = battle_id
                    battles_data.append(
                        {
                            "battle_id": battle_id,
                            "name": entry.trainer_name,
                            "difficulty": entry.difficulty,
                        }
                    )
                else:
                    battle_id = battle_lookup[key]
        else:
            battle_id = battle_lookup[(entry.trainer_name, entry.difficulty)]

        # Increment slot for this battle
        if battle_id not in battle_slots:
            battle_slots[battle_id] = 0
        battle_slots[battle_id] += 1
        slot = battle_slots[battle_id]

        pokemon_id_counter += 1
        pokemon_key = slugify(entry.pokemon)

        battle_pokemon_data.append(
            {
                "id": pokemon_id_counter,
                "battle_id": battle_id,
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
            battle_pokemon_moves_data.append(
                {
                    "battle_pokemon_id": pokemon_id_counter,
                    "move_key": move_key,
                    "slot": move_slot,
                }
            )

    # Add combined Elite Four + Champion battles
    _add_e4_champion_combined(
        battles_data,
        battle_pokemon_data,
        battle_pokemon_moves_data,
        battle_lookup,
        battle_slots,
        pokemon_id_counter,
    )

    # Create DataFrames
    battles_df = pl.DataFrame(battles_data)
    battle_pokemon_df = pl.DataFrame(battle_pokemon_data)
    battle_pokemon_moves_df = pl.DataFrame(battle_pokemon_moves_data)

    return battles_df, battle_pokemon_df, battle_pokemon_moves_df


def _group_by_int_key(
    data: list[dict[str, int | str | None]],
    key: str,
) -> dict[int, list[dict[str, int | str | None]]]:
    """Group a list of dicts by an integer key field.

    Args:
        data: List of dicts containing the key field.
        key: The key name whose integer value to group by.

    Returns:
        Dict mapping integer key values to lists of matching dicts.
    """
    result: dict[int, list[dict[str, int | str | None]]] = {}
    for item in data:
        int_key = int(item[key])  # type: ignore[arg-type]
        if int_key not in result:
            result[int_key] = []
        result[int_key].append(item)
    return result


def _group_moves_by_pokemon_id(
    moves_data: list[dict[str, int | str]],
) -> dict[int, list[dict[str, int | str]]]:
    """Group moves data by battle_pokemon_id.

    Args:
        moves_data: List of move dicts with battle_pokemon_id field.

    Returns:
        Dict mapping pokemon ID to lists of move dicts.
    """
    result: dict[int, list[dict[str, int | str]]] = {}
    for move in moves_data:
        pid = int(move["battle_pokemon_id"])
        if pid not in result:
            result[pid] = []
        result[pid].append(move)
    return result


def _add_e4_champion_combined(
    battles_data: list[dict[str, int | str | None]],
    battle_pokemon_data: list[dict[str, int | str | None]],
    battle_pokemon_moves_data: list[dict[str, int | str]],
    battle_lookup: dict[tuple[str, str | None], int],
    battle_slots: dict[int, int],
    pokemon_id_counter: int,
) -> None:
    """Add combined Elite Four + Champion battle entries.

    For each difficulty that has both E4 and Champion entries, creates an
    additional combined battle with all their Pokemon merged sequentially.
    Individual E4/Champion battles are kept unchanged.

    Args:
        battles_data: Mutable list of battle dicts (appended to).
        battle_pokemon_data: Mutable list of battle pokemon dicts (appended to).
        battle_pokemon_moves_data: Mutable list of move dicts (appended to).
        battle_lookup: Existing (name, difficulty) -> battle_id mapping.
        battle_slots: Existing battle_id -> slot count mapping.
        pokemon_id_counter: Current max pokemon ID (for assigning new IDs).
    """
    # Group E4/Champion battle_ids by difficulty
    e4_champion_by_difficulty: dict[str | None, list[int]] = {}
    for (name, difficulty), bid in battle_lookup.items():
        if name.startswith("Elite Four") or name.startswith("Champion"):
            if difficulty not in e4_champion_by_difficulty:
                e4_champion_by_difficulty[difficulty] = []
            e4_champion_by_difficulty[difficulty].append(bid)

    pokemon_by_battle = _group_by_int_key(battle_pokemon_data, "battle_id")
    moves_by_pokemon = _group_moves_by_pokemon_id(battle_pokemon_moves_data)

    for difficulty, battle_ids in e4_champion_by_difficulty.items():
        if len(battle_ids) < 2:  # noqa: PLR2004
            continue  # Need at least E4 + Champion to combine

        # Create combined battle entry
        combined_battle_id = len(battle_lookup) + 1
        combined_key = ("Elite Four + Champion", difficulty)
        battle_lookup[combined_key] = combined_battle_id
        battles_data.append(
            {
                "battle_id": combined_battle_id,
                "name": "Elite Four + Champion",
                "difficulty": difficulty,
            }
        )

        # Copy Pokemon from all E4/Champion battles with sequential slots
        combined_slot = 0
        for source_battle_id in sorted(battle_ids):
            for pkmn in pokemon_by_battle.get(source_battle_id, []):
                combined_slot += 1
                pokemon_id_counter += 1

                battle_pokemon_data.append(
                    {
                        "id": pokemon_id_counter,
                        "battle_id": combined_battle_id,
                        "pokemon_key": pkmn["pokemon_key"],
                        "slot": combined_slot,
                        "level": pkmn["level"],
                        "ability": pkmn["ability"],
                        "held_item": pkmn["held_item"],
                        "nature": pkmn["nature"],
                        "ev_hp": pkmn["ev_hp"],
                        "ev_attack": pkmn["ev_attack"],
                        "ev_defense": pkmn["ev_defense"],
                        "ev_sp_attack": pkmn["ev_sp_attack"],
                        "ev_sp_defense": pkmn["ev_sp_defense"],
                        "ev_speed": pkmn["ev_speed"],
                    }
                )

                # Copy moves for this Pokemon
                old_pokemon_id = int(pkmn["id"])  # type: ignore[arg-type]
                battle_pokemon_moves_data.extend(
                    {
                        "battle_pokemon_id": pokemon_id_counter,
                        "move_key": move["move_key"],
                        "slot": move["slot"],
                    }
                    for move in moves_by_pokemon.get(old_pokemon_id, [])
                )

        battle_slots[combined_battle_id] = combined_slot


def parse_showdown_file_to_dataframes(
    path: Path,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Parse Showdown format file directly to DataFrames.

    Args:
        path: Path to the Showdown/PokePaste format file.

    Returns:
        Tuple of (battles_df, battle_pokemon_df, battle_pokemon_moves_df).
    """
    content = path.read_text(encoding="utf-8")
    entries = parse_showdown_file(content)
    return entries_to_dataframes(entries)
