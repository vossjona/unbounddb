# ABOUTME: Loads game progression YAML and computes filter state from progression step.
# ABOUTME: Provides dropdown labels and LocationFilterConfig computation for the UI.

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.settings import settings

# Difficulties that use the "difficult" level cap column
_DIFFICULT_DIFFICULTIES = frozenset({"Difficult", "Expert", "Insane"})


@dataclass
class ProgressionEntry:
    """A single step in the game progression sequence.

    Attributes:
        step: 0-based index across both main game and post-game sections.
        trainer_name: Display name of the trainer, or None for game start.
        trainer_key: Slugified key for database matching, or None for game start.
        battle_type: Type of battle (GYM, RIVAL, BOSS, etc.), or None for game start.
        badge_number: Badge number (0-9) if this is a badge checkpoint, else None.
        locations: Locations unlocked after defeating this trainer.
        hm_unlocks: HMs unlocked after this battle.
        level_cap_vanilla: Level cap on vanilla difficulty, or None if unchanged.
        level_cap_difficult: Level cap on difficult+ difficulty, or None if unchanged.
        post_game: True if this entry is from the post-game section.
    """

    step: int
    trainer_name: str | None
    trainer_key: str | None
    battle_type: str | None
    badge_number: int | None
    locations: list[str] = field(default_factory=list)
    hm_unlocks: list[str] = field(default_factory=list)
    level_cap_vanilla: int | None = None
    level_cap_difficult: int | None = None
    post_game: bool = False


def _parse_entry(raw: dict[str, Any], step: int, post_game: bool) -> ProgressionEntry:
    """Parse a single YAML entry into a ProgressionEntry.

    Args:
        raw: Dictionary from YAML with trainer/locations/hm_unlocks etc.
        step: Sequential step index.
        post_game: Whether this entry is from the post_game section.

    Returns:
        Parsed ProgressionEntry.
    """
    return ProgressionEntry(
        step=step,
        trainer_name=raw.get("trainer"),
        trainer_key=raw.get("trainer_key"),
        battle_type=raw.get("battle_type"),
        badge_number=raw.get("badge_number"),
        locations=raw.get("locations") or [],
        hm_unlocks=raw.get("hm_unlocks") or [],
        level_cap_vanilla=raw.get("level_cap_vanilla"),
        level_cap_difficult=raw.get("level_cap_difficult"),
        post_game=post_game,
    )


@lru_cache(maxsize=1)
def load_progression(yaml_path: Path | None = None) -> tuple[ProgressionEntry, ...]:
    """Load game progression entries from the YAML config.

    Parses both the 'progression' and 'post_game' sections, assigning
    sequential step indices starting at 0.

    Args:
        yaml_path: Path to YAML file. Defaults to configs/game_progression.yml.

    Returns:
        Tuple of ProgressionEntry objects in order.
    """
    if yaml_path is None:
        yaml_path = settings.configs_dir / "game_progression.yml"

    with yaml_path.open() as f:
        data = yaml.safe_load(f)

    entries: list[ProgressionEntry] = []
    step = 0

    for raw in data.get("progression", []):
        entries.append(_parse_entry(raw, step, post_game=False))
        step += 1

    for raw in data.get("post_game", []):
        entries.append(_parse_entry(raw, step, post_game=True))
        step += 1

    return tuple(entries)


def get_dropdown_labels(entries: tuple[ProgressionEntry, ...] | list[ProgressionEntry]) -> list[str]:
    """Produce unique display labels for the trainer dropdown.

    Format rules:
    - Game start (step 0, no trainer): "Game Start (Lv X/Y)"
    - Gym badge: "Trainer Name (Gym - Badge N)"
    - Other battles: "Trainer Name (Battle Type)"
    - Duplicate trainer names get occurrence numbers: "Name (Type #N)"
    - Post-game entries prefixed: "[Post-Game] ..."

    Args:
        entries: Sequence of ProgressionEntry objects.

    Returns:
        List of display labels, one per entry.
    """
    # Count occurrences of each trainer name for dedup
    name_counts: dict[str, int] = {}
    for entry in entries:
        if entry.trainer_name is not None:
            name_counts[entry.trainer_name] = name_counts.get(entry.trainer_name, 0) + 1

    # Track which occurrence we're on for each trainer name
    name_seen: dict[str, int] = {}
    labels: list[str] = []

    for entry in entries:
        if entry.trainer_name is None:
            # Game start entry
            vanilla = entry.level_cap_vanilla or "?"
            difficult = entry.level_cap_difficult or "?"
            label = f"Game Start (Lv {vanilla}/{difficult})"
        else:
            name = entry.trainer_name
            battle_type = entry.battle_type or "Battle"

            # Build the parenthetical
            if entry.badge_number is not None and entry.badge_number > 0:
                detail = f"Gym - Badge {entry.badge_number}"
            else:
                detail = battle_type

            # Handle duplicate trainer names
            total = name_counts.get(name, 1)
            if total > 1:
                occurrence = name_seen.get(name, 0) + 1
                name_seen[name] = occurrence
                detail = f"{detail} #{occurrence}"

            label = f"{name} ({detail})"

            if entry.post_game:
                label = f"[Post-Game] {label}"

        labels.append(label)

    return labels


def compute_filter_config(
    entries: tuple[ProgressionEntry, ...] | list[ProgressionEntry],
    step: int,
    difficulty: str | None,
    rod_level: str = "None",
) -> LocationFilterConfig:
    """Compute a LocationFilterConfig by accumulating state from entries 0..step.

    Accumulates locations, HM unlocks, and level caps from the first entry
    through the entry at the given step index (inclusive).

    Args:
        entries: Full progression sequence.
        step: Index of the last completed step (inclusive).
        difficulty: Current difficulty setting (determines which level cap to use).
        rod_level: Current rod level, passed through to config.

    Returns:
        LocationFilterConfig reflecting the accumulated game state.
    """
    use_difficult = difficulty in _DIFFICULT_DIFFICULTIES

    accumulated_locations: list[str] = []
    accumulated_hms: set[str] = set()
    last_level_cap: int | None = None
    is_post_game = False

    clamped_step = min(step, len(entries) - 1) if entries else 0

    for entry in entries[: clamped_step + 1]:
        accumulated_locations.extend(entry.locations)
        accumulated_hms.update(entry.hm_unlocks)

        # Pick the right level cap column
        cap = entry.level_cap_difficult if use_difficult else entry.level_cap_vanilla
        if cap is not None:
            last_level_cap = cap

        if entry.post_game:
            is_post_game = True

    return LocationFilterConfig(
        has_surf="Surf" in accumulated_hms,
        has_dive="Dive" in accumulated_hms,
        has_rock_smash="Rock Smash" in accumulated_hms,
        post_game=is_post_game,
        rod_level=rod_level,
        accessible_locations=accumulated_locations if accumulated_locations else None,
        level_cap=last_level_cap,
    )
