# ABOUTME: Persistence layer for game progress settings with multi-profile support.
# ABOUTME: Delegates to user_database.py for storage, computes filters from progression data.

import streamlit as st

from unbounddb.app.browser_storage import (
    remove_profile_from_browser,
    sync_all_profiles_to_browser,
    sync_profile_to_browser,
)
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
from unbounddb.progression.progression_data import compute_filter_config, load_progression


def _get_default_config() -> LocationFilterConfig:
    """Return default config computed from step 0 of progression data."""
    entries = load_progression()
    return compute_filter_config(entries, step=0, difficulty=None)


@st.cache_data
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
    result = _db_create_profile(name)
    if result:
        get_all_profile_names.clear()
        sync_profile_to_browser(name)
    return result


def delete_profile_by_name(name: str) -> bool:
    """Delete a profile by name.

    Args:
        name: Profile name to delete.

    Returns:
        True if deleted, False if not found.
    """
    result = _db_delete_profile(name)
    if result:
        get_all_profile_names.clear()
        get_active_profile_name.clear()
        load_profile.clear()
        remove_profile_from_browser(name)
    return result


@st.cache_data
def load_profile(
    name: str | None,
) -> tuple[LocationFilterConfig | None, str | None, int, str]:
    """Load game progress config for a specific profile.

    Computes LocationFilterConfig from the profile's progression_step and
    difficulty using the progression YAML data.

    Args:
        name: Profile name, or None to ignore filters.

    Returns:
        Tuple of (config, difficulty, progression_step, rod_level).
        Returns (None, None, 0, "None") if name is None (ignore all filters).
    """
    if name is None:
        return None, None, 0, "None"

    data = _db_get_profile(name)

    if data is None:
        return _get_default_config(), None, 0, "None"

    progression_step = data.get("progression_step", 0)
    difficulty = data.get("difficulty")
    rod_level = data.get("rod_level", "None")

    entries = load_progression()
    config = compute_filter_config(entries, progression_step, difficulty, rod_level)
    return config, difficulty, progression_step, rod_level


def save_profile_progress(
    name: str,
    progression_step: int,
    rod_level: str,
    difficulty: str | None = None,
) -> None:
    """Save game progress fields to a profile.

    Args:
        name: Profile name to save to.
        progression_step: Index of the last defeated trainer.
        rod_level: Current rod level setting.
        difficulty: Optional difficulty setting to save.
    """
    _db_update_profile(
        name,
        progression_step=progression_step,
        rod_level=rod_level,
        difficulty=difficulty,
    )
    load_profile.clear()
    sync_profile_to_browser(name)


@st.cache_data
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
    get_active_profile_name.clear()
    sync_all_profiles_to_browser()
