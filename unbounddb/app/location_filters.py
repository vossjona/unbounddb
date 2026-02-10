# ABOUTME: Filter functions for Pokemon catch location data.
# ABOUTME: Provides filtering based on HMs, rods, accessibility, and game progress.

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocationFilterConfig:
    """Configuration for location filtering based on game progress.

    Attributes:
        has_surf: If False, exclude encounter_method == "surfing".
        has_dive: If False, exclude rows where encounter_notes contains "Underwater".
        rod_level: One of "None", "Old Rod", "Good Rod", "Super Rod".
        has_rock_smash: If False, exclude encounter_method == "rock_smash".
        post_game: If False, exclude Post-game locations and Beat the League requirements.
        accessible_locations: If not empty, only keep those location_names.
        level_cap: If set, exclude evolutions requiring level > this value.
        available_hms: Set of HM names available at current progression (for TM filtering).
    """

    has_surf: bool = True
    has_dive: bool = True
    rod_level: str = "Super Rod"
    has_rock_smash: bool = True
    post_game: bool = True
    accessible_locations: tuple[str, ...] | None = None
    level_cap: int | None = None
    available_hms: frozenset[str] = frozenset()


def _get_excluded_rod_methods(rod_level: str) -> set[str]:
    """Return encounter methods excluded by the current rod level.

    Args:
        rod_level: One of "None", "Old Rod", "Good Rod", "Super Rod".

    Returns:
        Set of encounter methods to exclude.
    """
    rod_exclusions: dict[str, set[str]] = {
        "None": {"old_rod", "good_rod", "super_rod"},
        "Old Rod": {"good_rod", "super_rod"},
        "Good Rod": {"super_rod"},
    }
    return rod_exclusions.get(rod_level, set())


def apply_location_filters(rows: list[dict[str, Any]], config: LocationFilterConfig | None) -> list[dict[str, Any]]:
    """Apply filters to location rows based on game progress.

    Args:
        rows: List of dicts with keys location_name, encounter_method, encounter_notes, requirement.
        config: Filter configuration specifying which encounters to include/exclude.
            If None, returns the list unchanged (no filtering).

    Returns:
        Filtered list (or original if config is None).
    """
    if config is None:
        return rows

    result = rows

    # 1. Surf filter
    if not config.has_surf:
        result = [r for r in result if r["encounter_method"] != "surfing"]

    # 2. Dive filter
    if not config.has_dive:
        result = [r for r in result if "Underwater" not in (r.get("encounter_notes") or "")]

    # 3. Rod filter
    rod_excluded = _get_excluded_rod_methods(config.rod_level)
    if rod_excluded:
        result = [r for r in result if r["encounter_method"] not in rod_excluded]

    # 4. Rock Smash filter
    if not config.has_rock_smash:
        result = [r for r in result if r["encounter_method"] != "rock_smash"]

    # 5. Post-game filter
    if not config.post_game:
        result = [
            r
            for r in result
            if "Post-game" not in (r.get("location_name") or "")
            and "Beat the League" not in (r.get("requirement") or "")
        ]

    # 6. Accessible locations filter
    if config.accessible_locations:
        accessible_set = set(config.accessible_locations)
        result = [r for r in result if r["location_name"] in accessible_set]

    return result
