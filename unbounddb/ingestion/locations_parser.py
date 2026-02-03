"""ABOUTME: Parses Pokemon location data from wide-format CSV.
ABOUTME: Transforms paired-column format into normalized location-pokemon entries."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

# Patterns to detect metadata/non-Pokemon rows
METADATA_PATTERNS = [
    r"^version\s*:?",  # Version markers
    r"^credits?\s*:?",  # Credits section
    r"^https?://",  # URLs (Discord, etc.)
    r"^discord",  # Discord links
    r"^\s*$",  # Empty rows
    r"^last\s+updated",  # Last updated markers
    r"^made\s+by",  # Attribution
]

METADATA_REGEX = re.compile("|".join(METADATA_PATTERNS), re.IGNORECASE)

# Patterns to detect encounter notes (not Pokemon names)
NOTE_PATTERNS = [
    r"^\d+F\s*-\s*\d+F$",  # Floor patterns like "4F - 1F"
    r"^\d+F$",  # Single floor like "2F"
    r"^B\d+F",  # Basement floors like "B1F"
    r"^swarm$",  # Swarm encounters
    r"^special\s+encounter",  # Special encounters
    r"^yellow\s+flowers?",  # Yellow flower grass
    r"^purple\s+flowers?",  # Purple flower grass
    r"^red\s+flowers?",  # Red flower grass
    r"^tall\s+grass",  # Tall grass
    r"^surfing",  # Surfing
    r"^fishing",  # Fishing
    r"^old\s+rod",  # Old Rod
    r"^good\s+rod",  # Good Rod
    r"^super\s+rod",  # Super Rod
    r"^rock\s+smash",  # Rock Smash
    r"^headbutt",  # Headbutt
    r"^honey\s+tree",  # Honey tree
    r"^grass$",  # Just "Grass"
    r"^water$",  # Just "Water"
    r"^cave$",  # Just "Cave"
    r"^morning$",  # Time of day
    r"^day$",  # Time of day
    r"^night$",  # Time of day
    r"^horde$",  # Horde encounters
    r"^hidden$",  # Hidden encounters
    r"^ambush$",  # Ambush encounters
    r"^gift$",  # Gift Pokemon
    r"^trade$",  # Trade Pokemon
    r"^static$",  # Static encounters
]

NOTE_REGEX = re.compile("|".join(NOTE_PATTERNS), re.IGNORECASE)


def _is_metadata_row(first_cell: str) -> bool:
    """Check if this row is metadata that should be skipped.

    Args:
        first_cell: First cell value of the row.

    Returns:
        True if this is a metadata row (version, credits, URLs, etc.).
    """
    if not first_cell or not first_cell.strip():
        return True
    return bool(METADATA_REGEX.search(first_cell.strip()))


def _is_note_not_pokemon(cell: str) -> bool:
    """Check if this cell is an encounter note, not a Pokemon name.

    Args:
        cell: Cell value to check.

    Returns:
        True if this is a note (floor pattern, Swarm, etc.), not a Pokemon.
    """
    if not cell or not cell.strip():
        return True
    return bool(NOTE_REGEX.match(cell.strip()))


def _extract_locations_from_header(header_row: list[str]) -> list[tuple[int, str]]:
    """Extract (column_index, location_name) pairs from header row.

    The CSV uses paired columns where location names appear in even columns
    (0, 2, 4, ...) and the odd columns are for additional data.

    Args:
        header_row: First row of the CSV.

    Returns:
        List of (column_index, location_name) tuples.
    """
    locations: list[tuple[int, str]] = []

    for idx, cell in enumerate(header_row):
        # Only look at even-indexed columns (0, 2, 4, ...)
        if idx % 2 != 0:
            continue

        cell_stripped = cell.strip() if cell else ""
        if cell_stripped and not _is_metadata_row(cell_stripped):
            locations.append((idx, cell_stripped))

    return locations


MIN_POKEMON_NAME_LENGTH = 3
SUSPICIOUS_CHARS = frozenset([":", "@", "#", "/", "\\", "(", ")", "[", "]"])


def _looks_like_pokemon_name(name: str) -> bool:
    """Check if string looks like a Pokemon name.

    Args:
        name: Potential Pokemon name.

    Returns:
        True if this looks like a valid Pokemon name.
    """
    name = name.strip()

    # Too short
    if len(name) < MIN_POKEMON_NAME_LENGTH:
        return False

    # Contains suspicious characters
    if any(c in SUSPICIOUS_CHARS for c in name):
        return False

    # Starts with number (likely a note)
    return not name[0].isdigit()


def _empty_locations_dataframe() -> pl.DataFrame:
    """Return an empty DataFrame with the correct schema for locations."""
    return pl.DataFrame(
        schema={
            "location_name": pl.String,
            "pokemon": pl.String,
            "pokemon_key": pl.String,
            "encounter_notes": pl.String,
        }
    )


@dataclass
class _ParseContext:
    """Mutable context for location parsing."""

    location_names: list[str]
    pokemon_names: list[str]
    encounter_notes: list[str]
    current_note: dict[int, str]


def _process_cell(cell: str, col_idx: int, location_name: str, ctx: _ParseContext) -> None:
    """Process a single cell, updating note tracking or adding Pokemon entry."""
    if _is_note_not_pokemon(cell):
        ctx.current_note[col_idx] = cell
    elif _looks_like_pokemon_name(cell):
        ctx.location_names.append(location_name)
        ctx.pokemon_names.append(cell)
        ctx.encounter_notes.append(ctx.current_note[col_idx])


def parse_locations_csv(path: Path) -> pl.DataFrame:
    """Parse wide-format locations CSV to normalized DataFrame.

    The input CSV has locations as column headers (in paired columns),
    with Pokemon names listed underneath each location.

    Args:
        path: Path to the locations CSV file.

    Returns:
        DataFrame with columns: location_name, pokemon, pokemon_key, encounter_notes.
    """
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return _empty_locations_dataframe()

    # Extract location columns from header
    header = rows[0]
    location_cols = _extract_locations_from_header(header)

    if not location_cols:
        return _empty_locations_dataframe()

    # Process data rows
    ctx = _ParseContext(
        location_names=[],
        pokemon_names=[],
        encounter_notes=[],
        current_note={col: "" for col, _ in location_cols},
    )

    for row in rows[1:]:
        if row and _is_metadata_row(row[0] if row else ""):
            continue

        for col_idx, location_name in location_cols:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip() if row[col_idx] else ""
            if cell:
                _process_cell(cell, col_idx, location_name, ctx)

    if not ctx.pokemon_names:
        return _empty_locations_dataframe()

    # Import here to avoid circular import with build module
    from unbounddb.build.normalize import slugify  # noqa: PLC0415

    df = pl.DataFrame(
        {
            "location_name": ctx.location_names,
            "pokemon": ctx.pokemon_names,
            "encounter_notes": ctx.encounter_notes,
        }
    )

    # Add slugified pokemon_key for joining
    df = df.with_columns(pl.col("pokemon").map_elements(slugify, return_dtype=pl.String).alias("pokemon_key"))

    return df
