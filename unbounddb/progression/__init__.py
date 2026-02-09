"""ABOUTME: Game progression extraction module for Pokemon Unbound.
ABOUTME: Parses walkthrough to extract trainer progression and location unlocks."""

from unbounddb.progression.dataclasses import (
    BadgeReward,
    ProgressionSegment,
    ProgressionUnlock,
    WalkthroughTrainer,
)
from unbounddb.progression.progression_data import (
    ProgressionEntry,
    compute_filter_config,
    get_dropdown_labels,
    load_progression,
)
from unbounddb.progression.walkthrough_parser import (
    BADGE_REWARDS,
    PROGRESSION_BATTLE_TYPES,
    WALKTHROUGH_URL,
    extract_locations_from_segment,
    extract_rod_upgrade,
    fetch_walkthrough,
    find_important_trainers,
    get_badge_reward,
    match_trainers_to_db,
    parse_walkthrough,
    save_progression_yaml,
    segment_by_trainers,
    unlocks_to_yaml,
)

__all__ = [
    "BADGE_REWARDS",
    "PROGRESSION_BATTLE_TYPES",
    "WALKTHROUGH_URL",
    "BadgeReward",
    "ProgressionEntry",
    "ProgressionSegment",
    "ProgressionUnlock",
    "WalkthroughTrainer",
    "compute_filter_config",
    "extract_locations_from_segment",
    "extract_rod_upgrade",
    "fetch_walkthrough",
    "find_important_trainers",
    "get_badge_reward",
    "get_dropdown_labels",
    "load_progression",
    "match_trainers_to_db",
    "parse_walkthrough",
    "save_progression_yaml",
    "segment_by_trainers",
    "unlocks_to_yaml",
]
