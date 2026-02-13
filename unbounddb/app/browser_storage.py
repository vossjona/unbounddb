# ABOUTME: Browser localStorage persistence for user profiles.
# ABOUTME: Syncs profiles between SQLite and browser localStorage to survive Streamlit Cloud restarts.

import json
import logging
from typing import Any

import streamlit as st
from streamlit_local_storage import LocalStorage

from unbounddb.app.user_database import (
    create_profile as _db_create_profile,
)
from unbounddb.app.user_database import (
    get_profile as _db_get_profile,
)
from unbounddb.app.user_database import (
    get_profile_count as _db_get_profile_count,
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

logger = logging.getLogger(__name__)

STORAGE_KEY = "unbounddb_profiles"
STORAGE_VERSION = 1


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable, no Streamlit dependency)
# ---------------------------------------------------------------------------


def parse_browser_data(raw: Any) -> list[dict[str, Any]] | None:
    """Parse raw localStorage value into a profile list.

    Handles str (JSON), dict (already parsed), None, and malformed data.

    Args:
        raw: Value from localStorage. Could be None, a JSON string, or a dict.

    Returns:
        List of profile dicts, or None if data is empty/malformed.
    """
    if raw is None:
        return None

    data: Any = raw
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(data, dict):
        return None

    if "profiles" not in data:
        return None

    profiles = data["profiles"]
    if not isinstance(profiles, list):
        return None

    return profiles


def upsert_profile(profiles: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace an existing profile by name or append a new one.

    Args:
        profiles: Current list of profile dicts.
        profile: Profile dict to upsert. Must contain a "name" key.

    Returns:
        Updated list with the profile inserted or replaced.
    """
    name = profile["name"]
    result = [p for p in profiles if p.get("name") != name]
    result.append(profile)
    return result


def remove_profile(profiles: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    """Remove a profile by name from the list.

    Args:
        profiles: Current list of profile dicts.
        name: Name of the profile to remove.

    Returns:
        New list without the named profile (no-op if not found).
    """
    return [p for p in profiles if p.get("name") != name]


# ---------------------------------------------------------------------------
# Streamlit-dependent functions
# ---------------------------------------------------------------------------


def _build_storage_payload(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the localStorage payload dict from a profile list.

    Args:
        profiles: List of profile dicts.

    Returns:
        Dict with version and profiles keys.
    """
    return {"version": STORAGE_VERSION, "profiles": profiles}


def get_profiles_from_browser() -> list[dict[str, Any]] | None:
    """Read all profiles from browser localStorage.

    Returns:
        List of profile dicts, or None if localStorage is empty or unavailable.
    """
    try:
        storage = LocalStorage()
        raw = storage.getItem(STORAGE_KEY)
    except Exception:
        # LocalStorage unavailable (no Streamlit runtime, JS disabled, etc.)
        return None
    return parse_browser_data(raw)


def save_profiles_to_browser(profiles: list[dict[str, Any]]) -> None:
    """Write all profiles to browser localStorage as JSON.

    Args:
        profiles: List of profile dicts to persist.
    """
    try:
        storage = LocalStorage()
        payload = _build_storage_payload(profiles)
        storage.setItem(STORAGE_KEY, payload)
    except Exception:
        # LocalStorage unavailable (no Streamlit runtime, JS disabled, etc.)
        logger.debug("Could not write to browser localStorage")


def sync_profile_to_browser(name: str) -> None:
    """Read one profile from SQLite and upsert it into browser localStorage.

    Args:
        name: Profile name to sync.
    """
    db_profile = _db_get_profile(name)
    if db_profile is None:
        return

    current = get_profiles_from_browser()
    profiles = current if current is not None else []
    updated = upsert_profile(profiles, db_profile)
    save_profiles_to_browser(updated)


def sync_all_profiles_to_browser() -> None:
    """Read ALL profiles from SQLite and write them to browser localStorage."""
    names = _db_list_profiles()
    profiles: list[dict[str, Any]] = []
    for name in names:
        data = _db_get_profile(name)
        if data is not None:
            profiles.append(data)
    save_profiles_to_browser(profiles)


def remove_profile_from_browser(name: str) -> None:
    """Remove one profile from browser localStorage.

    Args:
        name: Profile name to remove.
    """
    current = get_profiles_from_browser()
    if current is None:
        return
    updated = remove_profile(current, name)
    save_profiles_to_browser(updated)


def _restore_single_profile(profile: dict[str, Any]) -> bool:
    """Restore a single profile from browser data into SQLite.

    Args:
        profile: Profile dict from localStorage with name, fields, and active flag.

    Returns:
        True if the profile was restored, False if skipped.
    """
    name = profile.get("name")
    if not name or not isinstance(name, str):
        return False

    if not _db_create_profile(name):
        return False

    update_fields: dict[str, object] = {}
    for field in ("progression_step", "rod_level", "difficulty"):
        if field in profile:
            update_fields[field] = profile[field]

    if update_fields:
        _db_update_profile(name, db_path=None, **update_fields)

    if profile.get("active"):
        _db_set_active_profile(name)

    return True


def hydrate_db_from_browser() -> bool:
    """Populate SQLite from browser localStorage if the DB is empty.

    Runs at most once per Streamlit session. If the database already has
    profiles (session is alive), this is a no-op. If the database is empty
    (cold start after restart), it restores profiles from localStorage.

    Cache clearing is the caller's responsibility when this returns True.

    Returns:
        True if profiles were restored, False otherwise.
    """
    if st.session_state.get("_browser_hydration_done"):
        return False

    if _db_get_profile_count() > 0:
        st.session_state["_browser_hydration_done"] = True
        return False

    browser_profiles = get_profiles_from_browser()
    if not browser_profiles:
        # Don't set the flag: localStorage may not be available on first render.
        # Next rerun will retry and pick up the data once the component loads.
        return False

    restored = any(_restore_single_profile(p) for p in browser_profiles)

    if restored:
        logger.info("Hydrated profiles from browser localStorage")

    st.session_state["_browser_hydration_done"] = True
    return restored
