"""ABOUTME: Game progression extraction module for Pokemon Unbound.
ABOUTME: Parses walkthrough to extract trainer progression and location unlocks."""

from unbounddb.progression.dataclasses import (
    ProgressionSegment,
    ProgressionUnlock,
    WalkthroughTrainer,
)
from unbounddb.progression.walkthrough_parser import (
    WALKTHROUGH_URL,
    extract_hm_unlocks,
    extract_level_cap,
    extract_locations_from_segment,
    extract_rod_upgrade,
    fetch_walkthrough,
    find_important_trainers,
    match_trainers_to_db,
    parse_walkthrough,
    save_progression_yaml,
    segment_by_trainers,
    unlocks_to_yaml,
)

__all__ = [
    "WALKTHROUGH_URL",
    "ProgressionSegment",
    "ProgressionUnlock",
    "WalkthroughTrainer",
    "extract_hm_unlocks",
    "extract_level_cap",
    "extract_locations_from_segment",
    "extract_rod_upgrade",
    "fetch_walkthrough",
    "find_important_trainers",
    "match_trainers_to_db",
    "parse_walkthrough",
    "save_progression_yaml",
    "segment_by_trainers",
    "unlocks_to_yaml",
]
