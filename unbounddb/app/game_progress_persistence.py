# ABOUTME: Persistence layer for game progress settings.
# ABOUTME: Saves/loads LocationFilterConfig to JSON file in data directory.

import json
from typing import Any

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.settings import settings

GAME_PROGRESS_FILE = settings.data_dir / "game_progress.json"


def load_game_progress() -> LocationFilterConfig:
    """Load game progress config from JSON file.

    Returns:
        LocationFilterConfig with saved values, or defaults if file doesn't exist.
    """
    if not GAME_PROGRESS_FILE.exists():
        return LocationFilterConfig()

    try:
        with GAME_PROGRESS_FILE.open() as f:
            data = json.load(f)
        return LocationFilterConfig(
            has_surf=data.get("has_surf", True),
            has_dive=data.get("has_dive", True),
            rod_level=data.get("rod_level", "Super Rod"),
            has_rock_smash=data.get("has_rock_smash", True),
            post_game=data.get("post_game", True),
            accessible_locations=data.get("accessible_locations"),
            level_cap=data.get("level_cap"),
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        # If file is corrupted, return defaults
        return LocationFilterConfig()


def save_game_progress(config: LocationFilterConfig) -> None:
    """Save game progress config to JSON file.

    Args:
        config: The LocationFilterConfig to save.
    """
    data: dict[str, Any] = {
        "has_surf": config.has_surf,
        "has_dive": config.has_dive,
        "rod_level": config.rod_level,
        "has_rock_smash": config.has_rock_smash,
        "post_game": config.post_game,
        "accessible_locations": config.accessible_locations,
        "level_cap": config.level_cap,
    }

    # Ensure directory exists
    GAME_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with GAME_PROGRESS_FILE.open("w") as f:
        json.dump(data, f, indent=2)
