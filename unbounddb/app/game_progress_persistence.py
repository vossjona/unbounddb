# ABOUTME: Persistence layer for game progress settings with multi-profile support.
# ABOUTME: Saves/loads LocationFilterConfig to JSON file with named profiles (jonas, tim).

import json
from typing import Any

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.settings import settings

# Legacy single-profile file (for migration)
GAME_PROGRESS_FILE = settings.data_dir / "game_progress.json"

# New multi-profile file
GAME_PROFILES_FILE = settings.data_dir / "game_profiles.json"

# Available profile names
PROFILE_NAMES = ["jonas", "tim"]


def _config_to_dict(config: LocationFilterConfig) -> dict[str, Any]:
    """Convert LocationFilterConfig to dictionary for JSON serialization."""
    return {
        "has_surf": config.has_surf,
        "has_dive": config.has_dive,
        "rod_level": config.rod_level,
        "has_rock_smash": config.has_rock_smash,
        "post_game": config.post_game,
        "accessible_locations": config.accessible_locations,
        "level_cap": config.level_cap,
    }


def _dict_to_config(data: dict[str, Any]) -> LocationFilterConfig:
    """Convert dictionary to LocationFilterConfig."""
    return LocationFilterConfig(
        has_surf=data.get("has_surf", True),
        has_dive=data.get("has_dive", True),
        rod_level=data.get("rod_level", "Super Rod"),
        has_rock_smash=data.get("has_rock_smash", True),
        post_game=data.get("post_game", True),
        accessible_locations=data.get("accessible_locations"),
        level_cap=data.get("level_cap"),
    )


def _get_default_config() -> LocationFilterConfig:
    """Return fresh default config with no progress unlocked."""
    return LocationFilterConfig(
        has_surf=False,
        has_dive=False,
        rod_level="None",
        has_rock_smash=False,
        post_game=False,
        accessible_locations=None,
        level_cap=None,
    )


def _load_profiles_data() -> dict[str, Any]:
    """Load the raw profiles data from JSON file, migrating if needed."""
    _migrate_legacy_file()

    if not GAME_PROFILES_FILE.exists():
        # Create default profiles structure
        return {
            "profiles": {
                "jonas": _config_to_dict(_get_default_config()),
                "tim": _config_to_dict(_get_default_config()),
            },
            "active_profile": "jonas",
        }

    try:
        with GAME_PROFILES_FILE.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, TypeError):
        # If file is corrupted, return defaults
        return {
            "profiles": {
                "jonas": _config_to_dict(_get_default_config()),
                "tim": _config_to_dict(_get_default_config()),
            },
            "active_profile": "jonas",
        }


def _save_profiles_data(data: dict[str, Any]) -> None:
    """Save profiles data to JSON file."""
    GAME_PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with GAME_PROFILES_FILE.open("w") as f:
        json.dump(data, f, indent=2)


def _migrate_legacy_file() -> None:
    """Auto-migrate existing game_progress.json to jonas profile.

    Only runs once - if game_profiles.json already exists, does nothing.
    """
    if GAME_PROFILES_FILE.exists():
        return

    if not GAME_PROGRESS_FILE.exists():
        return

    # Load legacy data
    try:
        with GAME_PROGRESS_FILE.open() as f:
            legacy_data = json.load(f)
    except (json.JSONDecodeError, TypeError):
        return

    # Create new profiles structure with jonas having the legacy data
    profiles_data = {
        "profiles": {
            "jonas": legacy_data,
            "tim": _config_to_dict(_get_default_config()),
        },
        "active_profile": "jonas",
    }

    _save_profiles_data(profiles_data)


def load_profile(name: str | None) -> LocationFilterConfig | None:
    """Load game progress config for a specific profile.

    Args:
        name: Profile name ("jonas" or "tim"), or None to ignore filters.

    Returns:
        LocationFilterConfig with saved values for the profile,
        or None if name is None (signals: ignore all filters).
    """
    if name is None:
        return None

    data = _load_profiles_data()
    profile_data = data.get("profiles", {}).get(name)

    if profile_data is None:
        return _get_default_config()

    return _dict_to_config(profile_data)


def save_profile(name: str, config: LocationFilterConfig) -> None:
    """Save game progress config to a specific profile.

    Args:
        name: Profile name to save to ("jonas" or "tim").
        config: The LocationFilterConfig to save.
    """
    data = _load_profiles_data()

    if "profiles" not in data:
        data["profiles"] = {}

    data["profiles"][name] = _config_to_dict(config)
    _save_profiles_data(data)


def get_active_profile_name() -> str | None:
    """Get the currently selected profile name.

    Returns:
        Profile name ("jonas" or "tim") or None if filters are ignored.
    """
    data = _load_profiles_data()
    active = data.get("active_profile")

    # Validate that the profile is valid
    if active is None or active not in PROFILE_NAMES:
        return "jonas"  # Default to jonas

    return active


def set_active_profile(name: str | None) -> None:
    """Set the active profile.

    Args:
        name: Profile name ("jonas", "tim") or None to ignore filters.
    """
    data = _load_profiles_data()
    data["active_profile"] = name
    _save_profiles_data(data)


# Legacy functions for backwards compatibility
def load_game_progress() -> LocationFilterConfig:
    """Load game progress config from active profile.

    Returns:
        LocationFilterConfig with saved values, or defaults if not found.
    """
    active = get_active_profile_name()
    config = load_profile(active)
    return config if config is not None else LocationFilterConfig()


def save_game_progress(config: LocationFilterConfig) -> None:
    """Save game progress config to active profile.

    Args:
        config: The LocationFilterConfig to save.
    """
    active = get_active_profile_name()
    if active is not None:
        save_profile(active, config)
