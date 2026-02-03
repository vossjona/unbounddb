"""ABOUTME: Parser for TM and tutor compatibility files.
ABOUTME: Converts species lists from .txt files into a DataFrame of pokemon/move pairs."""

import re
from pathlib import Path

import polars as pl


def _extract_move_name(filename: str) -> str:
    """Extract move name from filename.

    Args:
        filename: Filename like "24 - Thunderbolt.txt" or "1 - Fire Punch.txt".

    Returns:
        Move name like "Thunderbolt" or "Fire Punch".
    """
    # Remove .txt extension
    name = filename.replace(".txt", "")

    # Pattern: "NN - Move Name" or "NNN - Move Name"
    match = re.match(r"\d+\s*-\s*(.+)", name)
    if match:
        return match.group(1).strip()

    return name


def _clean_species_name(species: str) -> str:
    """Convert species constant to readable name.

    Args:
        species: Species name like BULBASAUR, CHARIZARD_MEGA_X, or PIKACHU_SURFING.

    Returns:
        Cleaned name like Bulbasaur, Charizard Mega X, or Pikachu Surfing.
    """
    return species.replace("_", " ").title()


def parse_tm_tutor_file(path: Path, learn_method: str) -> pl.DataFrame:
    """Parse a single TM/tutor compatibility file.

    Args:
        path: Path to the .txt file.
        learn_method: Either "tm" or "tutor".

    Returns:
        DataFrame with pokemon_key, move_key, learn_method, level=None columns.
    """
    from unbounddb.build.normalize import slugify  # noqa: PLC0415

    content = path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Extract move name from filename
    move_name = _extract_move_name(path.name)
    move_key = slugify(move_name)

    # Parse species list (skip first line which is header like "TM01: Focus Punch")
    pokemon_keys: list[str] = []
    for line in lines[1:]:  # Skip header line
        species = line.strip()
        if not species:
            continue

        pokemon_key = slugify(_clean_species_name(species))
        pokemon_keys.append(pokemon_key)

    if not pokemon_keys:
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
            "pokemon_key": pokemon_keys,
            "move_key": [move_key] * len(pokemon_keys),
            "learn_method": [learn_method] * len(pokemon_keys),
            "level": [None] * len(pokemon_keys),
        }
    )


def parse_tm_tutor_directory(directory: Path, learn_method: str) -> pl.DataFrame:
    """Parse all files in a TM or tutor compatibility directory.

    Args:
        directory: Path to directory containing .txt files.
        learn_method: Either "tm" or "tutor".

    Returns:
        Combined DataFrame with pokemon_key, move_key, learn_method, level columns.
    """
    if not directory.exists():
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )

    # Find all .txt files
    txt_files = sorted(directory.glob("*.txt"))

    if not txt_files:
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )

    # Parse each file and concatenate
    dataframes = [parse_tm_tutor_file(f, learn_method) for f in txt_files]

    # Filter out empty DataFrames
    non_empty = [df for df in dataframes if len(df) > 0]

    if not non_empty:
        return pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )

    return pl.concat(non_empty)
