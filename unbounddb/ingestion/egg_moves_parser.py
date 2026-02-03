"""ABOUTME: Parser for Egg_Moves.c to extract Pokemon egg move data.
ABOUTME: Converts egg_moves() macro entries into a DataFrame of pokemon/move pairs."""

import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass
class EggMoveEntry:
    """Single egg move entry."""

    pokemon: str
    move: str


# Pattern to match egg_moves(SPECIES, MOVE1, MOVE2, ...) entries
# Captures species name and all moves in the block
EGG_MOVES_PATTERN = re.compile(
    r"egg_moves\s*\(\s*(\w+)\s*,([^)]+)\)",
    re.MULTILINE | re.DOTALL,
)

# Pattern to match individual MOVE_ constants
MOVE_PATTERN = re.compile(r"MOVE_(\w+)")


def _clean_species_name(species: str) -> str:
    """Convert species constant to readable name.

    Args:
        species: Species name like BULBASAUR or CHARIZARD_MEGA_X.

    Returns:
        Cleaned name like Bulbasaur or Charizard Mega X.
    """
    return species.replace("_", " ").title()


def _clean_move_name(move: str) -> str:
    """Convert MOVE_NAME to readable move name.

    Args:
        move: Move constant suffix like SKULLBASH or PETALDANCE.

    Returns:
        Cleaned name like Skull Bash or Petal Dance.
    """
    return move.replace("_", " ").title()


def parse_egg_moves(content: str) -> list[EggMoveEntry]:
    """Parse Egg_Moves.c content to extract egg moves.

    Args:
        content: Raw C file content.

    Returns:
        List of EggMoveEntry dataclasses.
    """
    entries: list[EggMoveEntry] = []

    for match in EGG_MOVES_PATTERN.finditer(content):
        species_name = match.group(1)
        moves_block = match.group(2)

        # Skip special entries
        if species_name in ("NONE", "EGG"):
            continue

        clean_pokemon = _clean_species_name(species_name)

        # Extract all move names from the block
        for move_match in MOVE_PATTERN.finditer(moves_block):
            move_name = move_match.group(1)

            # Skip NONE moves
            if move_name == "NONE":
                continue

            clean_move = _clean_move_name(move_name)
            entries.append(EggMoveEntry(pokemon=clean_pokemon, move=clean_move))

    return entries


def parse_egg_moves_file(path: Path) -> pl.DataFrame:
    """Parse Egg_Moves.c file to DataFrame.

    Args:
        path: Path to Egg_Moves.c file.

    Returns:
        DataFrame with pokemon_key, move_key, learn_method='egg', level=None columns.
    """
    from unbounddb.build.normalize import slugify  # noqa: PLC0415

    content = path.read_text(encoding="utf-8")
    entries = parse_egg_moves(content)

    if not entries:
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )

    return pl.DataFrame(
        {
            "pokemon_key": [slugify(e.pokemon) for e in entries],
            "move_key": [slugify(e.move) for e in entries],
            "learn_method": ["egg"] * len(entries),
            "level": [None] * len(entries),
        }
    )
