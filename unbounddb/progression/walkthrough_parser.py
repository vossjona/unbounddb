"""ABOUTME: Parser for Pokemon Unbound walkthrough to extract game progression.
ABOUTME: Extracts trainer order, location unlocks, HMs, level caps, and rod upgrades."""

import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from unbounddb.build.normalize import slugify
from unbounddb.progression.dataclasses import (
    ProgressionSegment,
    ProgressionUnlock,
    WalkthroughTrainer,
)

# Walkthrough URL
WALKTHROUGH_URL = (
    "https://www.pokemoncoders.com/wp-content/uploads/2022/04/"
    "Pokemon-Unbound-v2.0.3.2-18-January-2022-update-Walkthrough.txt"
)

# Post-game marker in the walkthrough
POST_GAME_MARKER = r"\\//\[\[POST-GAME ARC\]\]\\//|POST-GAME ARC"

# Regex patterns for important trainers
# These patterns look for trainer battle headers and extract the trainer name
TRAINER_PATTERNS = {
    "leader": re.compile(
        r">>?LEADER BATTLE<<?|Leader[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        re.IGNORECASE,
    ),
    "rival": re.compile(
        r">>?RIVAL BATTLE<<?.*?Rival\s+(\w+)",
        re.IGNORECASE | re.DOTALL,
    ),
    "boss": re.compile(
        r">>?(?:SHADOW\s+)?BOSS BATTLE<<?.*?\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\d|\n|-)",
        re.IGNORECASE,
    ),
    "shadow_admin": re.compile(
        r">>?SHADOW ADMIN BATTLE<<?.*?Shadow Admin\s+(\w+)",
        re.IGNORECASE | re.DOTALL,
    ),
    "elite_four": re.compile(
        r">>?ELITE FOUR<<?|Elite Four\s+(\w+)",
        re.IGNORECASE,
    ),
    "champion": re.compile(
        r">>?CHAMPION BATTLE<<?|Champion\s+(\w+)",
        re.IGNORECASE,
    ),
}

# Combined pattern to find any trainer battle marker
BATTLE_MARKER_PATTERN = re.compile(
    r">>([A-Z\s]+)BATTLE<<",
    re.IGNORECASE,
)

# Pattern to extract trainer name after battle marker
# Format: >>BATTLE TYPE<< \n =====+ or +++++\n Trainer Name \n - Pokemon
TRAINER_NAME_AFTER_MARKER = re.compile(
    r">>([A-Z\s]+)BATTLE<<\s*\n"  # Battle marker
    r"[=+]+\s*\n+"  # Separator line (=== or +++)
    r"([A-Za-z][A-Za-z\s&'.-]+?)"  # Trainer name (letters, spaces, &, ', -, .)
    r"\s*\n\s*-",  # Ends at newline followed by "-" (Pokemon list)
    re.IGNORECASE,
)

# Area code pattern for locations: [rt01], [dres], [froz]
AREA_CODE_PATTERN = re.compile(r"\[([a-z]+\d*)\]", re.IGNORECASE)

# Full location header pattern: [code] LOCATION NAME {Description}
LOCATION_HEADER_PATTERN = re.compile(
    r"\[([a-z]+\d*)\]\s+([A-Z][A-Z\s\d'-]+?)(?:\s*\{|\s*\"|\s*\n)",
    re.IGNORECASE,
)

# HM unlock patterns
HM_PATTERN = re.compile(
    r"we\s+can\s+now\s+use\s+(Cut|Surf|Rock\s*Smash|Strength|Fly|Waterfall|Dive|Flash)",
    re.IGNORECASE,
)

# Level cap pattern: "obey us until/up to LvXX"
LEVEL_CAP_PATTERN = re.compile(
    r"obey\s+us\s+(?:until|up\s+to)\s+Lv\.?\s*(\d+)",
    re.IGNORECASE,
)

# Rod upgrade patterns
ROD_PATTERN = re.compile(
    r"(?:received?|get|obtain(?:ed)?|got)\s+(?:the\s+)?(Old|Good|Super)\s+Rod",
    re.IGNORECASE,
)


async def fetch_walkthrough(url: str = WALKTHROUGH_URL) -> str:
    """Fetch walkthrough text from URL.

    Args:
        url: URL to fetch the walkthrough from.

    Returns:
        The walkthrough text content.

    Raises:
        httpx.HTTPError: If the fetch fails.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _normalize_trainer_name(name: str) -> str:
    """Normalize trainer name by cleaning up whitespace and formatting.

    Args:
        name: Raw trainer name from walkthrough.

    Returns:
        Cleaned trainer name.
    """
    # Remove extra whitespace
    name = " ".join(name.split())
    # Remove trailing punctuation
    name = name.rstrip("- :")
    return name.strip()


def find_important_trainers(content: str) -> list[WalkthroughTrainer]:
    """Find all important trainers in the walkthrough and their positions.

    Important trainers are: Leaders, Rivals, Bosses, Shadow Admins,
    Elite Four, and Champion.

    Args:
        content: Full walkthrough text.

    Returns:
        List of WalkthroughTrainer objects ordered by position in document.
    """
    trainers: list[WalkthroughTrainer] = []
    seen_positions: set[int] = set()

    # Find battle markers and extract trainer names
    for match in TRAINER_NAME_AFTER_MARKER.finditer(content):
        battle_type = match.group(1).strip().upper()
        trainer_name = _normalize_trainer_name(match.group(2))
        position = match.start()

        # Skip if we've already found a trainer at this position
        if position in seen_positions:
            continue
        seen_positions.add(position)

        # Skip generic entries or invalid names (minimum 3 chars)
        min_trainer_name_length = 3
        if not trainer_name or len(trainer_name) < min_trainer_name_length:
            continue

        # Add battle type prefix if not already present in the trainer name
        # GYM battles have "Leader X" as the trainer name already
        if battle_type in {"LEADER", "GYM"} and not trainer_name.lower().startswith("leader"):
            display_name = f"Leader {trainer_name}"
        elif battle_type == "RIVAL" and not trainer_name.lower().startswith("rival"):
            display_name = f"Rival {trainer_name}"
        elif battle_type == "SHADOW ADMIN" and "shadow admin" not in trainer_name.lower():
            display_name = f"Shadow Admin {trainer_name}"
        elif battle_type in {"BOSS", "SHADOW BOSS"}:
            # Boss names usually include their title
            display_name = trainer_name
        elif battle_type == "ELITE FOUR":
            display_name = f"Elite Four {trainer_name}"
        elif battle_type == "CHAMPION" and not trainer_name.lower().startswith("champion"):
            display_name = f"Champion {trainer_name}"
        else:
            display_name = trainer_name

        trainer_key = slugify(display_name)

        trainers.append(
            WalkthroughTrainer(
                name=display_name,
                trainer_key=trainer_key,
                position=position,
                matched_db_name=None,
            )
        )

    # Sort by position in document
    trainers.sort(key=lambda t: t.position)

    return trainers


def match_trainers_to_db(
    trainers: list[WalkthroughTrainer],
    db_trainer_names: list[str],
) -> list[WalkthroughTrainer]:
    """Match walkthrough trainers to database trainer names.

    Uses fuzzy matching to find the best match for each trainer.

    Args:
        trainers: List of trainers found in walkthrough.
        db_trainer_names: List of trainer names from database.

    Returns:
        Updated list with matched_db_name populated where matches found.
    """
    # Build lookup of slugified DB names
    db_lookup: dict[str, str] = {}
    for name in db_trainer_names:
        key = slugify(name)
        db_lookup[key] = name

    updated: list[WalkthroughTrainer] = []

    for trainer in trainers:
        matched_name = db_lookup.get(trainer.trainer_key)

        # Try partial matching if exact match not found
        if matched_name is None:
            # Try without common prefixes
            simplified_key = trainer.trainer_key
            for prefix in ["leader_", "rival_", "shadow_admin_", "elite_four_", "champion_"]:
                if simplified_key.startswith(prefix):
                    simplified_key = simplified_key[len(prefix) :]
                    break

            # Look for DB names containing the simplified key
            for db_key, db_name in db_lookup.items():
                if simplified_key in db_key or db_key in trainer.trainer_key:
                    matched_name = db_name
                    break

        updated.append(
            WalkthroughTrainer(
                name=trainer.name,
                trainer_key=trainer.trainer_key,
                position=trainer.position,
                matched_db_name=matched_name,
            )
        )

    return updated


def segment_by_trainers(
    content: str,
    trainers: list[WalkthroughTrainer],
) -> list[ProgressionSegment]:
    """Split walkthrough content into segments by trainer positions.

    Each segment contains the content between defeating one trainer
    and the next important trainer battle.

    Args:
        content: Full walkthrough text.
        trainers: Ordered list of important trainers.

    Returns:
        List of ProgressionSegment objects.
    """
    segments: list[ProgressionSegment] = []

    # First segment: from start to first trainer
    if trainers:
        first_segment_text = content[: trainers[0].position]
        segments.append(
            ProgressionSegment(
                segment_index=0,
                after_trainer=None,
                text=first_segment_text,
            )
        )

    # Segments between trainers
    for i, trainer in enumerate(trainers):
        # Find end of this segment (start of next trainer or end of content)
        end_pos = trainers[i + 1].position if i + 1 < len(trainers) else len(content)
        segment_text = content[trainer.position : end_pos]

        segments.append(
            ProgressionSegment(
                segment_index=i + 1,
                after_trainer=trainer,
                text=segment_text,
            )
        )

    return segments


def extract_locations_from_segment(
    segment: ProgressionSegment,
    known_locations: list[str],
) -> list[str]:
    """Extract location names from a segment that match known DB locations.

    Args:
        segment: The progression segment to analyze.
        known_locations: List of known location names from database.

    Returns:
        List of matched location names found in the segment.
    """
    found_locations: list[str] = []
    text = segment.text

    # Build lookup of slugified known locations
    location_lookup: dict[str, str] = {}
    for loc in known_locations:
        key = slugify(loc)
        location_lookup[key] = loc

    # Find location headers in the segment
    for match in LOCATION_HEADER_PATTERN.finditer(text):
        location_name = match.group(2).strip()
        location_key = slugify(location_name)

        # Try exact match
        if location_key in location_lookup:
            matched = location_lookup[location_key]
            if matched not in found_locations:
                found_locations.append(matched)
            continue

        # Try partial match (location name contains or is contained by known)
        for known_key, known_name in location_lookup.items():
            if known_key in location_key or location_key in known_key:
                if known_name not in found_locations:
                    found_locations.append(known_name)
                break

    return found_locations


def extract_hm_unlocks(segment: ProgressionSegment) -> list[str]:
    """Extract HM unlock mentions from a segment.

    Args:
        segment: The progression segment to analyze.

    Returns:
        List of HM names that are unlocked (e.g., ["Cut", "Surf"]).
    """
    hm_unlocks: list[str] = []

    for match in HM_PATTERN.finditer(segment.text):
        hm_name = match.group(1).strip()
        # Normalize Rock Smash
        hm_name = hm_name.replace(" ", " ").title()
        if hm_name == "Rock Smash":
            hm_name = "Rock Smash"
        if hm_name not in hm_unlocks:
            hm_unlocks.append(hm_name)

    return hm_unlocks


def extract_level_cap(segment: ProgressionSegment) -> int | None:
    """Extract level cap from a segment.

    Args:
        segment: The progression segment to analyze.

    Returns:
        New level cap if found, None otherwise.
    """
    matches = list(LEVEL_CAP_PATTERN.finditer(segment.text))
    if matches:
        # Return the last (highest) level cap mentioned
        return int(matches[-1].group(1))
    return None


def extract_rod_upgrade(segment: ProgressionSegment) -> str | None:
    """Extract rod upgrade from a segment.

    Args:
        segment: The progression segment to analyze.

    Returns:
        Rod type if found (e.g., "Old Rod"), None otherwise.
    """
    match = ROD_PATTERN.search(segment.text)
    if match:
        rod_type = match.group(1).title()
        return f"{rod_type} Rod"
    return None


def _is_post_game_segment(content: str, segment: ProgressionSegment) -> bool:
    """Check if a segment is in the post-game section.

    Args:
        content: Full walkthrough text.
        segment: The segment to check.

    Returns:
        True if segment is after the post-game marker.
    """
    # Find all post-game markers and use the last one (first is in table of contents)
    matches = list(re.finditer(POST_GAME_MARKER, content))
    if matches:
        last_marker = matches[-1]
        return segment.after_trainer is not None and segment.after_trainer.position > last_marker.start()
    return False


def parse_walkthrough(
    content: str,
    known_locations: list[str] | None = None,
    db_trainer_names: list[str] | None = None,
) -> list[ProgressionUnlock]:
    """Parse walkthrough content to extract full game progression.

    Args:
        content: Full walkthrough text.
        known_locations: List of known location names for matching.
        db_trainer_names: List of trainer names from DB for matching.

    Returns:
        Ordered list of ProgressionUnlock objects representing game progression.
    """
    if known_locations is None:
        known_locations = []
    if db_trainer_names is None:
        db_trainer_names = []

    # Phase 1: Find important trainers
    trainers = find_important_trainers(content)

    # Phase 2: Match to DB trainers
    if db_trainer_names:
        trainers = match_trainers_to_db(trainers, db_trainer_names)

    # Phase 3: Segment walkthrough
    segments = segment_by_trainers(content, trainers)

    # Phase 4: Extract progression data from each segment
    unlocks: list[ProgressionUnlock] = []

    for segment in segments:
        trainer_name = segment.after_trainer.name if segment.after_trainer else None
        trainer_key = segment.after_trainer.trainer_key if segment.after_trainer else None

        locations = extract_locations_from_segment(segment, known_locations)
        hm_unlocks = extract_hm_unlocks(segment)
        level_cap = extract_level_cap(segment)
        rod_upgrade = extract_rod_upgrade(segment)
        post_game = _is_post_game_segment(content, segment)

        unlocks.append(
            ProgressionUnlock(
                trainer_name=trainer_name,
                trainer_key=trainer_key,
                locations=locations,
                hm_unlocks=hm_unlocks,
                level_cap=level_cap,
                rod_upgrade=rod_upgrade,
                post_game=post_game,
            )
        )

    return unlocks


def unlocks_to_yaml(
    unlocks: list[ProgressionUnlock],
    walkthrough_url: str = WALKTHROUGH_URL,
) -> str:
    """Convert progression unlocks to YAML format.

    Args:
        unlocks: List of ProgressionUnlock objects.
        walkthrough_url: URL of the source walkthrough.

    Returns:
        YAML string representation.
    """
    # Separate main game and post-game
    main_game = [u for u in unlocks if not u.post_game]
    post_game = [u for u in unlocks if u.post_game]

    def unlock_to_dict(u: ProgressionUnlock) -> dict[str, str | int | list[str] | None]:
        """Convert single unlock to dict for YAML."""
        d: dict[str, str | int | list[str] | None] = {
            "trainer": u.trainer_name,
            "trainer_key": u.trainer_key,
            "locations": u.locations if u.locations else [],
            "hm_unlocks": u.hm_unlocks if u.hm_unlocks else [],
        }
        if u.level_cap is not None:
            d["level_cap"] = u.level_cap
        if u.rod_upgrade is not None:
            d["rod"] = u.rod_upgrade
        return d

    data = {
        "walkthrough_url": walkthrough_url,
        "extraction_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "coverage": "Full main story through Champion + partial post-game",
        "post_game_marker": "[[POST-GAME ARC]]",
        "progression": [unlock_to_dict(u) for u in main_game],
    }

    if post_game:
        data["post_game"] = [unlock_to_dict(u) for u in post_game]

    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_progression_yaml(
    unlocks: list[ProgressionUnlock],
    output_path: Path,
    walkthrough_url: str = WALKTHROUGH_URL,
) -> None:
    """Save progression data to YAML file.

    Args:
        unlocks: List of ProgressionUnlock objects.
        output_path: Path to save the YAML file.
        walkthrough_url: URL of the source walkthrough.
    """
    yaml_content = unlocks_to_yaml(unlocks, walkthrough_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml_content, encoding="utf-8")
