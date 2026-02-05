"""ABOUTME: Parses Pokemon location data from multiple CSV formats.
ABOUTME: Supports Grass/Cave, Surfing/Fishing, and Gift/Static encounter CSVs."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

# Constants for CSV parsing
MIN_ROWS_FOR_HEADER = 4
MIN_ROW_LENGTH = 4
GIFT_STATIC_LOCATION_COL = 2
GIFT_STATIC_REQUIREMENT_COL = 7
GIFT_STATIC_POKEMON_COL_START = 4
GIFT_STATIC_POKEMON_COL_END = 7

# Keywords that indicate a cave location (for encounter_method detection)
CAVE_KEYWORDS = frozenset(
    [
        "cave",
        "tunnel",
        "mountain",
        "volcano",
        "ruins",
        "tomb",
        "sewers",
        "mt.",
        "mt ",
    ]
)

# Floor patterns like "4F - 1F", "B1F", "2F"
FLOOR_PATTERN = re.compile(r"^(?:B?\d+F(?:\s*-\s*B?\d+F)?|B\d+F.*)$", re.IGNORECASE)

# Method markers for Surfing/Fishing CSV
WATER_METHOD_MARKERS = {
    "Surfing": "surfing",
    "Old Rod": "old_rod",
    "Good Rod": "good_rod",
    "Super Rod": "super_rod",
    "Rock Smash": "rock_smash",
}

# Sublocation markers for Surfing/Fishing CSV
SUBLOCATION_MARKERS = {
    "Small Island",
    "West",
    "East",
    "Underwater",
    "Inside",
    "Outside",
    "Special Encounter",
}

# Gift/Static method mapping
GIFT_STATIC_METHODS = {
    "gift": "gift",
    "static": "static",
    "mission reward": "mission_reward",
    "random egg": "random_egg",
}

# Patterns to detect metadata/non-Pokemon rows
METADATA_PATTERNS = [
    r"^version\s*:?",
    r"^credits?\s*:?",
    r"^https?://",
    r"^discord",
    r"^\s*$",
    r"^last\s+updated",
    r"^made\s+by",
    r"^current\s+game\s+version",
    r"^unbound's\s+discord",
    r"^other\s+useful\s+guides",
    r"^pokémon\s+unbound\s+location\s+guide",
    r"^orange\s+color",
    r"^purple\s+color",
]

METADATA_REGEX = re.compile("|".join(METADATA_PATTERNS), re.IGNORECASE)

# Minimum length for a valid Pokemon name
MIN_POKEMON_NAME_LENGTH = 3

# Characters that indicate this is not a Pokemon name
SUSPICIOUS_CHARS = frozenset([":", "@", "#", "\\", "[", "]"])

# Strings that are not Pokemon names
NON_POKEMON_STRINGS = frozenset(
    ["x", "fishing", "surfing", "rock smash", "special encounter", "easy", "medium", "hard", "insane"]
)


def _is_metadata_row(first_cell: str) -> bool:
    """Check if this row is metadata that should be skipped.

    Only returns True if the first cell explicitly contains metadata text.
    Empty first cells are NOT treated as metadata - the row might have data in other columns.
    """
    if not first_cell or not first_cell.strip():
        return False  # Empty cell is not metadata, row might have data in other columns
    return bool(METADATA_REGEX.search(first_cell.strip()))


def _is_floor_pattern(cell: str) -> bool:
    """Check if cell is a floor pattern like '4F - 1F', 'B1F'."""
    return bool(FLOOR_PATTERN.match(cell.strip()))


def _looks_like_pokemon_name(name: str) -> bool:
    """Check if string looks like a Pokemon name."""
    name = name.strip()

    if len(name) < MIN_POKEMON_NAME_LENGTH:
        return False

    if any(c in SUSPICIOUS_CHARS for c in name):
        return False

    # Starts with number (likely a note like "1F")
    if name[0].isdigit():
        return False

    # Skip known non-Pokemon strings
    return name.lower() not in NON_POKEMON_STRINGS


def _detect_encounter_method(location_name: str) -> str:
    """Detect if location is cave or grass based on name."""
    lower = location_name.lower()
    for keyword in CAVE_KEYWORDS:
        if keyword in lower:
            return "cave"
    return "grass"


def _empty_locations_dataframe() -> pl.DataFrame:
    """Return an empty DataFrame with the correct schema for locations."""
    return pl.DataFrame(
        schema={
            "location_name": pl.String,
            "pokemon": pl.String,
            "pokemon_key": pl.String,
            "encounter_method": pl.String,
            "encounter_notes": pl.String,
            "requirement": pl.String,
        }
    )


def _extract_locations_from_header(header_row: list[str]) -> list[tuple[int, str]]:
    """Extract (column_index, location_name) pairs from header row.

    The CSV uses paired columns where location names appear in even columns
    (0, 2, 4, ...) and the odd columns are for additional data.
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


def _add_slugified_pokemon_key(df: pl.DataFrame) -> pl.DataFrame:
    """Add pokemon_key column to DataFrame."""
    from unbounddb.build.normalize import slugify  # noqa: PLC0415

    return df.with_columns(pl.col("pokemon").map_elements(slugify, return_dtype=pl.String).alias("pokemon_key"))


def _entries_to_dataframe(entries: list[dict[str, str]]) -> pl.DataFrame:
    """Convert entries list to DataFrame with pokemon_key."""
    if not entries:
        return _empty_locations_dataframe()
    df = pl.DataFrame(entries)
    return _add_slugified_pokemon_key(df)


@dataclass
class _GrassCaveSectionState:
    """Track section state for a column in Grass & Cave CSV."""

    is_swarm: bool = False
    is_special: bool = False
    floor: str = ""

    def build_notes(self) -> str:
        """Build encounter notes from current state."""
        notes: list[str] = []
        if self.is_swarm:
            notes.append("Swarm")
        if self.is_special:
            notes.append("Special Encounter")
        if self.floor:
            notes.append(self.floor)
        return ", ".join(notes) if notes else ""


def _process_grass_cave_cell(
    cell: str,
    col_idx: int,
    location_name: str,
    section_state: dict[int, _GrassCaveSectionState],
    entries: list[dict[str, str]],
) -> None:
    """Process a single cell from Grass & Cave CSV."""
    if cell == "Swarm":
        section_state[col_idx].is_swarm = True
        section_state[col_idx].is_special = False
        section_state[col_idx].floor = ""
    elif cell == "Special Encounter":
        section_state[col_idx].is_special = True
    elif _is_floor_pattern(cell):
        section_state[col_idx].floor = cell
    elif _looks_like_pokemon_name(cell):
        entries.append(
            {
                "location_name": location_name,
                "pokemon": cell,
                "encounter_method": _detect_encounter_method(location_name),
                "encounter_notes": section_state[col_idx].build_notes(),
                "requirement": "",
            }
        )


def parse_grass_cave_csv(path: Path) -> pl.DataFrame:
    """Parse Grass & Cave Encounters CSV to normalized DataFrame.

    Args:
        path: Path to the Grass & Cave CSV file.

    Returns:
        DataFrame with columns: location_name, pokemon, pokemon_key,
        encounter_method, encounter_notes, requirement.
    """
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return _empty_locations_dataframe()

    header = rows[0]
    location_cols = _extract_locations_from_header(header)

    if not location_cols:
        return _empty_locations_dataframe()

    section_state: dict[int, _GrassCaveSectionState] = {col: _GrassCaveSectionState() for col, _ in location_cols}
    entries: list[dict[str, str]] = []

    for row in rows[1:]:
        if row and _is_metadata_row(row[0] if row else ""):
            continue

        for col_idx, location_name in location_cols:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip() if row[col_idx] else ""
            if cell:
                _process_grass_cave_cell(cell, col_idx, location_name, section_state, entries)

    return _entries_to_dataframe(entries)


@dataclass
class _SurfingFishingState:
    """Track state for a column in Surfing/Fishing CSV."""

    method: str = "surfing"
    sublocation: str = ""


def _process_surfing_cell(
    cell: str,
    col_idx: int,
    location_name: str,
    state: dict[int, _SurfingFishingState],
    entries: list[dict[str, str]],
) -> None:
    """Process a single cell from Surfing/Fishing CSV."""
    if cell in WATER_METHOD_MARKERS:
        state[col_idx].method = WATER_METHOD_MARKERS[cell]
        state[col_idx].sublocation = ""
    elif cell in {"Fishing", "X"}:
        pass  # Skip
    elif cell in SUBLOCATION_MARKERS or _is_floor_pattern(cell):
        state[col_idx].sublocation = cell
    elif _looks_like_pokemon_name(cell):
        entries.append(
            {
                "location_name": location_name,
                "pokemon": cell,
                "encounter_method": state[col_idx].method,
                "encounter_notes": state[col_idx].sublocation,
                "requirement": "",
            }
        )


def parse_surfing_fishing_csv(path: Path) -> pl.DataFrame:
    """Parse Surfing, Fishing, Rock Smash CSV to normalized DataFrame.

    Args:
        path: Path to the Surfing/Fishing CSV file.

    Returns:
        DataFrame with columns: location_name, pokemon, pokemon_key,
        encounter_method, encounter_notes, requirement.
    """
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < MIN_ROWS_FOR_HEADER:
        return _empty_locations_dataframe()

    # Row 0: "Surfing" header, Row 1: Empty, Row 2: Location names
    header = rows[2]
    location_cols = _extract_locations_from_header(header)

    if not location_cols:
        return _empty_locations_dataframe()

    state: dict[int, _SurfingFishingState] = {col: _SurfingFishingState() for col, _ in location_cols}
    entries: list[dict[str, str]] = []

    for row in rows[3:]:
        if row and _is_metadata_row(row[0] if row else ""):
            continue

        for col_idx, location_name in location_cols:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip() if row[col_idx] else ""
            if cell:
                _process_surfing_cell(cell, col_idx, location_name, state, entries)

    return _entries_to_dataframe(entries)


@dataclass
class _GiftStaticRowContext:
    """Context for parsing a row in Gift/Static CSV."""

    method: str = ""
    location: str = ""
    requirement: str = ""


def _parse_gift_static_row(row: list[str], ctx: _GiftStaticRowContext) -> list[dict[str, str]]:
    """Parse a single row from Gift/Static CSV and return entries."""
    if len(row) < MIN_ROW_LENGTH:
        return []

    method_cell = row[0].strip() if row[0] else ""
    location = _extract_gift_static_location(row)
    pokemon_cells = _extract_gift_static_pokemon(row)
    requirement = (
        row[GIFT_STATIC_REQUIREMENT_COL].strip()
        if len(row) > GIFT_STATIC_REQUIREMENT_COL and row[GIFT_STATIC_REQUIREMENT_COL]
        else ""
    )

    # Handle continuation rows
    if not method_cell and not location:
        method_cell = ctx.method
        location = ctx.location
        if not requirement:
            requirement = ctx.requirement
    else:
        ctx.method = method_cell
        ctx.location = location
        ctx.requirement = requirement

    encounter_method = GIFT_STATIC_METHODS.get(method_cell.lower(), method_cell.lower().replace(" ", "_"))

    if not encounter_method:
        return []

    entries: list[dict[str, str]] = []
    for pokemon in pokemon_cells:
        entries.extend(_create_pokemon_entries(pokemon, location, encounter_method, requirement))

    return entries


def _extract_gift_static_location(row: list[str]) -> str:
    """Extract location from Gift/Static CSV row (column 2)."""
    if len(row) > GIFT_STATIC_LOCATION_COL and row[GIFT_STATIC_LOCATION_COL]:
        return row[GIFT_STATIC_LOCATION_COL].strip()
    return ""


def _extract_gift_static_pokemon(row: list[str]) -> list[str]:
    """Extract Pokemon names from Gift/Static CSV row (columns 4-6)."""
    pokemon_cells: list[str] = []
    for i in range(GIFT_STATIC_POKEMON_COL_START, min(GIFT_STATIC_POKEMON_COL_END, len(row))):
        cell = row[i].strip() if row[i] else ""
        if cell and _looks_like_pokemon_name(cell):
            pokemon_cells.append(cell)
    return pokemon_cells


def _create_pokemon_entries(
    pokemon: str, location: str, encounter_method: str, requirement: str
) -> list[dict[str, str]]:
    """Create entries for a Pokemon, handling alternatives like 'Voltorb/Electrode'."""
    entries: list[dict[str, str]] = []
    if "/" in pokemon:
        for part in pokemon.split("/"):
            stripped_part = part.strip()
            if stripped_part and _looks_like_pokemon_name(stripped_part):
                entries.append(_make_entry(location, stripped_part, encounter_method, requirement))
    else:
        entries.append(_make_entry(location, pokemon, encounter_method, requirement))
    return entries


def _make_entry(location: str, pokemon: str, encounter_method: str, requirement: str) -> dict[str, str]:
    """Create a single entry dict."""
    return {
        "location_name": location,
        "pokemon": pokemon,
        "encounter_method": encounter_method,
        "encounter_notes": "",
        "requirement": requirement,
    }


def parse_gift_static_csv(path: Path) -> pl.DataFrame:
    """Parse Gift & Static Encounters CSV to normalized DataFrame.

    Args:
        path: Path to the Gift/Static CSV file.

    Returns:
        DataFrame with columns: location_name, pokemon, pokemon_key,
        encounter_method, encounter_notes, requirement.
    """
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < MIN_ROWS_FOR_HEADER:
        return _empty_locations_dataframe()

    entries: list[dict[str, str]] = []
    ctx = _GiftStaticRowContext()

    for row in rows[3:]:
        entries.extend(_parse_gift_static_row(row, ctx))

    return _entries_to_dataframe(entries)


def parse_all_location_csvs(source_dir: Path) -> pl.DataFrame:
    """Parse all location CSVs and combine into unified DataFrame.

    Args:
        source_dir: Directory containing the location CSV files.

    Returns:
        Combined DataFrame with all location data.
    """
    dataframes: list[pl.DataFrame] = []

    # Find and parse Grass & Cave CSV
    grass_cave_files = list(source_dir.glob("*Grass*Cave*.csv"))
    for csv_path in grass_cave_files:
        df = parse_grass_cave_csv(csv_path)
        if len(df) > 0:
            dataframes.append(df)

    # Find and parse Surfing/Fishing CSV
    surfing_files = list(source_dir.glob("*Surfing*Fishing*.csv"))
    for csv_path in surfing_files:
        df = parse_surfing_fishing_csv(csv_path)
        if len(df) > 0:
            dataframes.append(df)

    # Find and parse Gift/Static CSV
    gift_static_files = list(source_dir.glob("*Gift*Static*.csv"))
    for csv_path in gift_static_files:
        df = parse_gift_static_csv(csv_path)
        if len(df) > 0:
            dataframes.append(df)

    if not dataframes:
        return _empty_locations_dataframe()

    return pl.concat(dataframes)


# Backward compatibility - keep old function signature
def parse_locations_csv(path: Path) -> pl.DataFrame:
    """Parse wide-format locations CSV to normalized DataFrame.

    This is the legacy function. For new code, use parse_grass_cave_csv,
    parse_surfing_fishing_csv, parse_gift_static_csv, or parse_all_location_csvs.

    Args:
        path: Path to the locations CSV file.

    Returns:
        DataFrame with columns: location_name, pokemon, pokemon_key,
        encounter_method, encounter_notes, requirement.
    """
    return parse_grass_cave_csv(path)
