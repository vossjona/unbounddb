"""ABOUTME: Game progression extraction module for Pokemon Unbound.
ABOUTME: Parses walkthrough to extract trainer progression and location unlocks."""

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from unbounddb.progression.walkthrough_parser import (
        BADGE_REWARDS as BADGE_REWARDS,
    )
    from unbounddb.progression.walkthrough_parser import (
        PROGRESSION_BATTLE_TYPES as PROGRESSION_BATTLE_TYPES,
    )
    from unbounddb.progression.walkthrough_parser import (
        WALKTHROUGH_URL as WALKTHROUGH_URL,
    )
    from unbounddb.progression.walkthrough_parser import (
        extract_locations_from_segment as extract_locations_from_segment,
    )
    from unbounddb.progression.walkthrough_parser import (
        extract_rod_upgrade as extract_rod_upgrade,
    )
    from unbounddb.progression.walkthrough_parser import (
        fetch_walkthrough as fetch_walkthrough,
    )
    from unbounddb.progression.walkthrough_parser import (
        find_important_trainers as find_important_trainers,
    )
    from unbounddb.progression.walkthrough_parser import (
        get_badge_reward as get_badge_reward,
    )
    from unbounddb.progression.walkthrough_parser import (
        match_trainers_to_db as match_trainers_to_db,
    )
    from unbounddb.progression.walkthrough_parser import (
        parse_walkthrough as parse_walkthrough,
    )
    from unbounddb.progression.walkthrough_parser import (
        save_progression_yaml as save_progression_yaml,
    )
    from unbounddb.progression.walkthrough_parser import (
        segment_by_trainers as segment_by_trainers,
    )
    from unbounddb.progression.walkthrough_parser import (
        unlocks_to_yaml as unlocks_to_yaml,
    )

_LAZY_IMPORTS = {
    "BADGE_REWARDS",
    "PROGRESSION_BATTLE_TYPES",
    "WALKTHROUGH_URL",
    "extract_locations_from_segment",
    "extract_rod_upgrade",
    "fetch_walkthrough",
    "find_important_trainers",
    "get_badge_reward",
    "match_trainers_to_db",
    "parse_walkthrough",
    "save_progression_yaml",
    "segment_by_trainers",
    "unlocks_to_yaml",
}


def __getattr__(name: str) -> object:
    """Lazy-import walkthrough_parser names to avoid loading httpx at import time."""
    if name in _LAZY_IMPORTS:
        import unbounddb.progression.walkthrough_parser as wp  # noqa: PLC0415

        return getattr(wp, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
