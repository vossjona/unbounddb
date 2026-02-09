"""ABOUTME: Parser for Pokemon Unbound walkthrough to extract game progression.
ABOUTME: Extracts trainer order, location unlocks, badge rewards, level caps, and rod upgrades."""

import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from unbounddb.build.normalize import slugify
from unbounddb.progression.dataclasses import (
    BadgeReward,
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

# Preamble marker — the walkthrough text starts here (skips table of contents)
PREAMBLE_MARKER = "Hello there"

# Battle types that gate story progression (excludes optional/legendary battles)
PROGRESSION_BATTLE_TYPES: frozenset[str] = frozenset(
    {
        "RIVAL",
        "GYM",
        "MEGA GYM",
        "SHADOW ADMIN",
        "SHADOW BOSS",
        "BOSS",
        "ELITE 4",
        "BORRIUS LEAGUE CHAMPIONSHIP",
        "EX SHADOW ADMIN",
        "LIGHT OF RUIN ADMIN",
        "LIGHT OF RUIN LEADER",
    }
)

# Hardcoded badge rewards: badge → level caps → HM unlocks
# Data from game files, not parsed from walkthrough text
BADGE_REWARDS: list[BadgeReward] = [
    BadgeReward(badge_number=0, trainer_key="__game_start__", level_cap_vanilla=15, level_cap_difficult=20),
    BadgeReward(badge_number=1, trainer_key="leader_mirskle", level_cap_vanilla=22, level_cap_difficult=26),
    BadgeReward(
        badge_number=2, trainer_key="leader_vega", level_cap_vanilla=29, level_cap_difficult=32, hm_unlocks=["Cut"]
    ),
    BadgeReward(
        badge_number=3,
        trainer_key="leader_alice",
        level_cap_vanilla=33,
        level_cap_difficult=36,
        hm_unlocks=["Rock Smash"],
    ),
    BadgeReward(
        badge_number=4,
        trainer_key="leader_mel",
        level_cap_vanilla=37,
        level_cap_difficult=40,
        hm_unlocks=["Fly", "Strength"],
    ),
    BadgeReward(
        badge_number=5,
        trainer_key="successor_maxima",
        level_cap_vanilla=43,
        level_cap_difficult=45,
        hm_unlocks=["Surf"],
    ),
    BadgeReward(badge_number=6, trainer_key="leader_galavan", level_cap_vanilla=51, level_cap_difficult=52),
    BadgeReward(
        badge_number=7,
        trainer_key="leader_big_mo",
        level_cap_vanilla=55,
        level_cap_difficult=57,
        hm_unlocks=["Rock Climb"],
    ),
    BadgeReward(
        badge_number=8,
        trainer_key="leader_tessy",
        level_cap_vanilla=60,
        level_cap_difficult=61,
        hm_unlocks=["Waterfall"],
    ),
    BadgeReward(badge_number=9, trainer_key="leader_benjamin", level_cap_vanilla=66, level_cap_difficult=75),
]

# O(1) lookup by trainer_key
_BADGE_REWARDS_BY_KEY: dict[str, BadgeReward] = {br.trainer_key: br for br in BADGE_REWARDS}

# HMs unlocked in post-game (not tied to a specific badge)
POST_GAME_HM_UNLOCKS: list[str] = ["Dive"]

# Pattern to extract trainer name after battle marker
# Format: >>BATTLE TYPE<< \n <any separator line>\n Trainer Name \n - Pokemon
TRAINER_NAME_AFTER_MARKER = re.compile(
    r">>([A-Z][A-Z\s]+?)\s*BATTLE<<\s*\n"  # >>TYPE BATTLE<<
    r"[^\n]+\n"  # Any separator line (===, +++, xxx, ooo, MmM, etc.)
    r"\s*\n*"  # Optional blank lines
    r"([^\n][^\n]*?)"  # Trainer name (any chars, including accented)
    r"\s*\n\s*-\s",  # Followed by "- " (team list)
)

# Area code pattern for locations: [rt01], [dres], [froz]
AREA_CODE_PATTERN = re.compile(r"\[([a-z]+\d*)\]", re.IGNORECASE)

# Full location header pattern: [code] LOCATION NAME {Description}
LOCATION_HEADER_PATTERN = re.compile(
    r"\[([a-z]+\d*)\]\s+([A-Z][A-Z\s\d'-]+?)(?:\s*\{|\s*\"|\s*\n)",
    re.IGNORECASE,
)

# Rod upgrade patterns
ROD_PATTERN = re.compile(
    r"(?:received?|get|obtain(?:ed)?|got)\s+(?:the\s+)?(Old|Good|Super)\s+Rod",
    re.IGNORECASE,
)


def _strip_preamble(content: str) -> str:
    """Strip table of contents / preamble before the actual walkthrough.

    Args:
        content: Full walkthrough text.

    Returns:
        Walkthrough text starting from the preamble marker.
    """
    idx = content.find(PREAMBLE_MARKER)
    return content[idx:] if idx != -1 else content


def _normalize_battle_type(raw: str) -> str:
    """Normalize battle type by collapsing whitespace and uppercasing.

    Handles double spaces like "LIGHT OF RUIN  ADMIN" → "LIGHT OF RUIN ADMIN".

    Args:
        raw: Raw battle type string from regex match.

    Returns:
        Normalized uppercase battle type.
    """
    return " ".join(raw.split()).upper()


def get_badge_reward(trainer_key: str) -> BadgeReward | None:
    """Look up badge reward data by trainer key.

    Args:
        trainer_key: Slugified trainer key.

    Returns:
        BadgeReward if the trainer awards a badge, None otherwise.
    """
    return _BADGE_REWARDS_BY_KEY.get(trainer_key)


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
        # Server sends text/plain without charset; actual encoding is Latin-1
        response.encoding = "latin-1"
        return response.text


def _normalize_trainer_name(name: str) -> str:
    """Normalize trainer name by cleaning up whitespace and formatting.

    Args:
        name: Raw trainer name from walkthrough.

    Returns:
        Cleaned trainer name.
    """
    name = " ".join(name.split())
    name = name.rstrip("- :")
    return name.strip()


def _build_display_name(battle_type: str, trainer_name: str) -> str:
    """Build a display name by prepending the appropriate title prefix.

    Args:
        battle_type: Normalized battle type (e.g., "GYM", "RIVAL").
        trainer_name: Raw trainer name from walkthrough.

    Returns:
        Display name with title prefix if needed.
    """
    name_lower = trainer_name.lower()

    # Map battle types to (prefix, check_function)
    # GYM / MEGA GYM → "Leader" (unless already has Leader/Successor)
    if battle_type in {"GYM", "MEGA GYM"}:
        if not name_lower.startswith(("leader", "successor")):
            return f"Leader {trainer_name}"
        return trainer_name

    # Boss names keep their own title
    if battle_type in {"BOSS", "SHADOW BOSS"}:
        return trainer_name

    # Simple prefix mappings
    prefix_map: dict[str, tuple[str, str]] = {
        "RIVAL": ("Rival", "rival"),
        "SHADOW ADMIN": ("Shadow Admin", "shadow admin"),
        "EX SHADOW ADMIN": ("Shadow Admin", "shadow admin"),
        "ELITE 4": ("Elite Four", "elite four"),
        "BORRIUS LEAGUE CHAMPIONSHIP": ("Champion", "champion"),
        "LIGHT OF RUIN ADMIN": ("Light of Ruin Admin", "admin"),
        "LIGHT OF RUIN LEADER": ("Light of Ruin Leader", "leader"),
    }

    if battle_type in prefix_map:
        prefix, check_str = prefix_map[battle_type]
        if check_str not in name_lower:
            return f"{prefix} {trainer_name}"

    return trainer_name


def find_important_trainers(
    content: str,
    *,
    progression_only: bool = True,
) -> list[WalkthroughTrainer]:
    """Find all important trainers in the walkthrough and their positions.

    Args:
        content: Full walkthrough text.
        progression_only: If True, only return trainers whose battle type
            gates story progression (excludes legendary/optional battles).

    Returns:
        List of WalkthroughTrainer objects ordered by position in document.
    """
    trainers: list[WalkthroughTrainer] = []
    seen_positions: set[int] = set()

    for match in TRAINER_NAME_AFTER_MARKER.finditer(content):
        raw_battle_type = match.group(1).strip()
        battle_type = _normalize_battle_type(raw_battle_type)
        trainer_name = _normalize_trainer_name(match.group(2))
        position = match.start()

        if position in seen_positions:
            continue
        seen_positions.add(position)

        min_trainer_name_length = 3
        if not trainer_name or len(trainer_name) < min_trainer_name_length:
            continue

        if progression_only and battle_type not in PROGRESSION_BATTLE_TYPES:
            continue

        display_name = _build_display_name(battle_type, trainer_name)
        trainer_key = slugify(display_name)

        trainers.append(
            WalkthroughTrainer(
                name=display_name,
                trainer_key=trainer_key,
                position=position,
                battle_type=battle_type,
            )
        )

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
    db_lookup: dict[str, str] = {}
    for name in db_trainer_names:
        key = slugify(name)
        db_lookup[key] = name

    updated: list[WalkthroughTrainer] = []

    for trainer in trainers:
        matched_name = db_lookup.get(trainer.trainer_key)

        if matched_name is None:
            simplified_key = trainer.trainer_key
            for prefix in [
                "leader_",
                "rival_",
                "shadow_admin_",
                "elite_four_",
                "champion_",
                "successor_",
                "light_of_ruin_admin_",
                "light_of_ruin_leader_",
            ]:
                if simplified_key.startswith(prefix):
                    simplified_key = simplified_key[len(prefix) :]
                    break

            for db_key, db_name in db_lookup.items():
                if simplified_key in db_key or db_key in trainer.trainer_key:
                    matched_name = db_name
                    break

        updated.append(
            WalkthroughTrainer(
                name=trainer.name,
                trainer_key=trainer.trainer_key,
                position=trainer.position,
                battle_type=trainer.battle_type,
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

    if trainers:
        first_segment_text = content[: trainers[0].position]
        segments.append(
            ProgressionSegment(
                segment_index=0,
                after_trainer=None,
                text=first_segment_text,
            )
        )

    for i, trainer in enumerate(trainers):
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

    location_lookup: dict[str, str] = {}
    for loc in known_locations:
        key = slugify(loc)
        location_lookup[key] = loc

    for match in LOCATION_HEADER_PATTERN.finditer(text):
        location_name = match.group(2).strip()
        location_key = slugify(location_name)

        if location_key in location_lookup:
            matched = location_lookup[location_key]
            if matched not in found_locations:
                found_locations.append(matched)
            continue

        for known_key, known_name in location_lookup.items():
            if known_key in location_key or location_key in known_key:
                if known_name not in found_locations:
                    found_locations.append(known_name)
                break

    return found_locations


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

    Strips the preamble (table of contents), finds progression-relevant
    trainers, and uses hardcoded badge reward data for level caps and HMs.

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

    # Strip preamble (table of contents) before actual walkthrough
    content = _strip_preamble(content)

    # Phase 1: Find progression-relevant trainers
    trainers = find_important_trainers(content, progression_only=True)

    # Phase 2: Match to DB trainers
    if db_trainer_names:
        trainers = match_trainers_to_db(trainers, db_trainer_names)

    # Phase 3: Segment walkthrough
    segments = segment_by_trainers(content, trainers)

    # Phase 4: Extract progression data from each segment
    unlocks: list[ProgressionUnlock] = []
    first_post_game_seen = False

    for segment in segments:
        trainer_name = segment.after_trainer.name if segment.after_trainer else None
        trainer_key = segment.after_trainer.trainer_key if segment.after_trainer else None
        battle_type = segment.after_trainer.battle_type if segment.after_trainer else None
        post_game = _is_post_game_segment(content, segment)

        locations = extract_locations_from_segment(segment, known_locations)
        rod_upgrade = extract_rod_upgrade(segment)

        # Use hardcoded badge rewards for level caps and HMs
        badge_reward: BadgeReward | None = None
        if trainer_key is None:
            # Game start — use badge 0
            badge_reward = _BADGE_REWARDS_BY_KEY.get("__game_start__")
        else:
            badge_reward = get_badge_reward(trainer_key)

        hm_unlocks: list[str] = badge_reward.hm_unlocks if badge_reward else []
        level_cap_vanilla = badge_reward.level_cap_vanilla if badge_reward else None
        level_cap_difficult = badge_reward.level_cap_difficult if badge_reward else None
        badge_number = badge_reward.badge_number if badge_reward else None

        # Attach post-game HMs to the first post-game segment
        if post_game and not first_post_game_seen:
            first_post_game_seen = True
            hm_unlocks = [*hm_unlocks, *POST_GAME_HM_UNLOCKS]

        unlocks.append(
            ProgressionUnlock(
                trainer_name=trainer_name,
                trainer_key=trainer_key,
                battle_type=battle_type,
                badge_number=badge_number,
                locations=locations,
                hm_unlocks=hm_unlocks,
                level_cap_vanilla=level_cap_vanilla,
                level_cap_difficult=level_cap_difficult,
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
    main_game = [u for u in unlocks if not u.post_game]
    post_game = [u for u in unlocks if u.post_game]

    def unlock_to_dict(u: ProgressionUnlock) -> dict[str, str | int | list[str] | None]:
        """Convert single unlock to dict for YAML."""
        d: dict[str, str | int | list[str] | None] = {
            "trainer": u.trainer_name,
            "trainer_key": u.trainer_key,
            "battle_type": u.battle_type,
            "badge_number": u.badge_number,
            "locations": u.locations if u.locations else [],
            "hm_unlocks": u.hm_unlocks if u.hm_unlocks else [],
        }
        if u.level_cap_vanilla is not None:
            d["level_cap_vanilla"] = u.level_cap_vanilla
        if u.level_cap_difficult is not None:
            d["level_cap_difficult"] = u.level_cap_difficult
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
