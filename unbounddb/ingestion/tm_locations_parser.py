# ABOUTME: Parser for TM locations CSV data from the Google Sheets source.
# ABOUTME: Extracts TM number, move name, location, and required HMs from free-text PLACE column.

import re
from pathlib import Path

import polars as pl

from unbounddb.build.normalize import slugify

# Aliases mapping TM PLACE location names to progression location names.
# Discovered by comparing parsed locations against game_progression.yml locations.
_LOCATION_ALIASES: dict[str, str] = {
    "Dehara Dept": "Dehara City",
    "Thundercap Mountain": "Epidimy Town",
    "Thundercap Mt": "Epidimy Town",
    "Forst Mountain": "Frost Mountain",
    "Redwood Forest": "Redwood Village",
    "Antisis Sewers": "Antisis City",
}

# TMs purchasable at the Battle Tower are post-game only
_POST_GAME_LOCATIONS = frozenset({"Battle Tower"})

# HM patterns to search for within parenthetical/bracket context in the PLACE text.
# Each tuple is (compiled regex, canonical HM name).
_HM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\bsurf\b"), "Surf"),
    (re.compile(r"(?i)\bcut\b"), "Cut"),
    (re.compile(r"(?i)\brock\s*climb\b"), "Rock Climb"),
    (re.compile(r"(?i)\brock\s*smash\b"), "Rock Smash"),
    (re.compile(r"(?i)\bstrength\b|\bstrengh\b"), "Strength"),
    (re.compile(r"(?i)\bwaterfall\b"), "Waterfall"),
    (re.compile(r"(?i)\b(?:dive|adm)\b"), "Dive"),
]


def _extract_base_location(place: str) -> str:
    """Extract the base location name from a PLACE string.

    Takes the text before the first '(' or '[', stripped of whitespace.

    Args:
        place: Raw PLACE text from the CSV.

    Returns:
        Base location name (e.g. "Valley Cave" from "Valley Cave (on B1F after using Rock Climb)").
    """
    # Find the first opening delimiter
    paren_idx = place.find("(")
    bracket_idx = place.find("[")

    cut_idx = len(place)
    if paren_idx != -1:
        cut_idx = paren_idx
    if bracket_idx != -1:
        cut_idx = min(cut_idx, bracket_idx)

    return place[:cut_idx].strip()


def _extract_context_text(place: str) -> str:
    """Extract the parenthetical/bracketed context from a PLACE string.

    This is the text inside parentheses and brackets where HM requirements
    are typically mentioned. Returns just this portion so we don't match
    HM names that happen to be in location names.

    Args:
        place: Raw PLACE text from the CSV.

    Returns:
        Combined text from within parentheses and brackets.
    """
    parts = [match.group(1) for match in re.finditer(r"[\(\[]([^\)\]]*)", place)]
    return " ".join(parts)


def _extract_required_hms(place: str) -> list[str]:
    """Extract HM requirements from the context portion of a PLACE string.

    Only searches within parenthetical/bracket text to avoid false positives
    from location names (e.g. "Surf" in "Surfside City").

    Args:
        place: Raw PLACE text from the CSV.

    Returns:
        Sorted list of canonical HM names required (e.g. ["Rock Climb", "Surf"]).
    """
    context = _extract_context_text(place)
    if not context:
        return []

    found: set[str] = set()
    for pattern, hm_name in _HM_PATTERNS:
        if pattern.search(context):
            found.add(hm_name)

    return sorted(found)


def _resolve_location(base_location: str) -> str:
    """Resolve a base location name to its canonical progression name.

    Applies alias mapping for known mismatches between the TM spreadsheet
    and the game_progression.yml location names.

    Args:
        base_location: Base location extracted from PLACE text.

    Returns:
        Canonical location name matching progression data.
    """
    return _LOCATION_ALIASES.get(base_location, base_location)


def parse_tm_locations_csv(path: Path) -> pl.DataFrame:
    """Parse TM locations CSV into a structured DataFrame.

    Reads the CSV with columns ID, NAME, TYPE, PLACE and extracts:
    - TM number and move name
    - Base location (resolved to progression names)
    - Required HMs for access
    - Post-game flag for Battle Tower purchases

    Args:
        path: Path to the tm_locations.csv file.

    Returns:
        DataFrame with columns: tm_number, move_name, move_key, location,
        required_hms, place_raw, is_post_game.
    """
    raw_df = pl.read_csv(path, encoding="utf-8")

    rows: list[dict[str, int | str | bool]] = []
    for row in raw_df.iter_rows(named=True):
        tm_number = int(row["ID"])
        move_name = str(row["NAME"]).strip()
        place_raw = str(row["PLACE"]).strip()

        base_location = _extract_base_location(place_raw)
        location = _resolve_location(base_location)
        required_hms = _extract_required_hms(place_raw)
        is_post_game = base_location in _POST_GAME_LOCATIONS

        rows.append(
            {
                "tm_number": tm_number,
                "move_name": move_name,
                "move_key": slugify(move_name),
                "location": location,
                "required_hms": ",".join(required_hms),
                "place_raw": place_raw,
                "is_post_game": is_post_game,
            }
        )

    return pl.DataFrame(rows)
