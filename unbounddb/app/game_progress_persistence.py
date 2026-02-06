# ABOUTME: Persistence layer for game progress settings with multi-profile support.
# ABOUTME: Delegates to user_database.py for DuckDB storage with dynamic profile creation.

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.app.user_database import (
    create_profile as _db_create_profile,
)
from unbounddb.app.user_database import (
    delete_profile as _db_delete_profile,
)
from unbounddb.app.user_database import (
    get_active_profile as _db_get_active_profile,
)
from unbounddb.app.user_database import (
    get_profile as _db_get_profile,
)
from unbounddb.app.user_database import (
    list_profiles as _db_list_profiles,
)
from unbounddb.app.user_database import (
    set_active_profile as _db_set_active_profile,
)
from unbounddb.app.user_database import (
    update_profile as _db_update_profile,
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


def get_all_profile_names() -> list[str]:
    """Get all profile names from the database.

    Returns:
        List of profile names, sorted alphabetically.
    """
    return _db_list_profiles()


def create_new_profile(name: str) -> bool:
    """Create a new profile with default settings.

    Args:
        name: Profile name to create.

    Returns:
        True if created successfully, False if name already exists.
    """
    return _db_create_profile(name)


def delete_profile_by_name(name: str) -> bool:
    """Delete a profile by name.

    Args:
        name: Profile name to delete.

    Returns:
        True if deleted, False if not found.
    """
    return _db_delete_profile(name)


def load_profile(name: str | None) -> tuple[LocationFilterConfig | None, str | None]:
    """Load game progress config for a specific profile.

    Args:
        name: Profile name, or None to ignore filters.

    Returns:
        Tuple of (LocationFilterConfig, difficulty) for the profile.
        Returns (None, None) if name is None (signals: ignore all filters).
    """
    if name is None:
        return None, None

    data = _db_get_profile(name)

    if data is None:
        return _get_default_config(), None

    config = LocationFilterConfig(
        has_surf=data.get("has_surf", False),
        has_dive=data.get("has_dive", False),
        rod_level=data.get("rod_level", "None"),
        has_rock_smash=data.get("has_rock_smash", False),
        post_game=data.get("post_game", False),
        accessible_locations=data.get("accessible_locations"),
        level_cap=data.get("level_cap"),
    )
    difficulty = data.get("difficulty")

    return config, difficulty


def save_profile(name: str, config: LocationFilterConfig, difficulty: str | None = None) -> None:
    """Save game progress config to a specific profile.

    Args:
        name: Profile name to save to.
        config: The LocationFilterConfig to save.
        difficulty: Optional difficulty setting to save.
    """
    _db_update_profile(
        name,
        has_surf=config.has_surf,
        has_dive=config.has_dive,
        rod_level=config.rod_level,
        has_rock_smash=config.has_rock_smash,
        post_game=config.post_game,
        accessible_locations=config.accessible_locations,
        level_cap=config.level_cap,
        difficulty=difficulty,
    )


def get_active_profile_name() -> str | None:
    """Get the currently selected profile name.

    Returns:
        Profile name or None if filters are ignored.
    """
    return _db_get_active_profile()


def set_active_profile(name: str | None) -> None:
    """Set the active profile.

    Args:
        name: Profile name or None to ignore filters.
    """
    _db_set_active_profile(name)


# Legacy functions for backwards compatibility
def load_game_progress() -> LocationFilterConfig:
    """Load game progress config from active profile.

    Returns:
        LocationFilterConfig with saved values, or defaults if not found.
    """
    active = get_active_profile_name()
    config, _ = load_profile(active)
    return config if config is not None else LocationFilterConfig()


def save_game_progress(config: LocationFilterConfig) -> None:
    """Save game progress config to active profile.

    Args:
        config: The LocationFilterConfig to save.
    """
    active = get_active_profile_name()
    if active is not None:
        # Preserve existing difficulty when saving just the config
        _, existing_difficulty = load_profile(active)
        save_profile(active, config, difficulty=existing_difficulty)
