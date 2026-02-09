# ABOUTME: Filter functions for Pokemon catch location data.
# ABOUTME: Provides filtering based on HMs, rods, accessibility, and game progress.

from dataclasses import dataclass

import polars as pl


@dataclass
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
    accessible_locations: list[str] | None = None
    level_cap: int | None = None
    available_hms: frozenset[str] = frozenset()


def apply_location_filters(df: pl.DataFrame, config: LocationFilterConfig | None) -> pl.DataFrame:
    """Apply filters to location DataFrame based on game progress.

    Args:
        df: DataFrame with columns location_name, encounter_method, encounter_notes, requirement.
        config: Filter configuration specifying which encounters to include/exclude.
            If None, returns the DataFrame unchanged (no filtering).

    Returns:
        Filtered DataFrame (or original if config is None).
    """
    if config is None:
        return df

    result = df

    # 1. Surf filter
    if not config.has_surf:
        result = result.filter(pl.col("encounter_method") != "surfing")

    # 2. Dive filter
    if not config.has_dive:
        result = result.filter(~pl.col("encounter_notes").str.contains("Underwater"))

    # 3. Rod filter
    if config.rod_level == "None":
        result = result.filter(~pl.col("encounter_method").is_in(["old_rod", "good_rod", "super_rod"]))
    elif config.rod_level == "Old Rod":
        result = result.filter(~pl.col("encounter_method").is_in(["good_rod", "super_rod"]))
    elif config.rod_level == "Good Rod":
        result = result.filter(pl.col("encounter_method") != "super_rod")
    # "Super Rod" keeps all

    # 4. Rock Smash filter
    if not config.has_rock_smash:
        result = result.filter(pl.col("encounter_method") != "rock_smash")

    # 5. Post-game filter
    if not config.post_game:
        result = result.filter(
            ~pl.col("location_name").str.contains("Post-game") & ~pl.col("requirement").str.contains("Beat the League")
        )

    # 6. Accessible locations filter
    if config.accessible_locations:
        result = result.filter(pl.col("location_name").is_in(config.accessible_locations))

    return result
