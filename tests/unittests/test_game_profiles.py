# ABOUTME: Tests for multi-profile game progress persistence.
# ABOUTME: Verifies profile loading, saving, migration, and None config handling.

import json
from pathlib import Path

import polars as pl
import pytest

from unbounddb.app.game_progress_persistence import (
    PROFILE_NAMES,
    _migrate_legacy_file,
    get_active_profile_name,
    load_profile,
    save_profile,
    set_active_profile,
)
from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters


@pytest.fixture
def clean_profile_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a clean temporary data directory and patch file paths."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Patch the file paths to use temp directory
    monkeypatch.setattr(
        "unbounddb.app.game_progress_persistence.GAME_PROFILES_FILE",
        data_dir / "game_profiles.json",
    )
    monkeypatch.setattr(
        "unbounddb.app.game_progress_persistence.GAME_PROGRESS_FILE",
        data_dir / "game_progress.json",
    )

    return data_dir


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_profile_returns_none_for_none_input(self, clean_profile_files: Path) -> None:
        """Loading profile with None returns None."""
        result = load_profile(None)

        assert result is None

    def test_load_profile_returns_config_for_named_profile(self, clean_profile_files: Path) -> None:
        """Loading a named profile returns LocationFilterConfig."""
        result = load_profile("jonas")

        assert isinstance(result, LocationFilterConfig)

    def test_load_profile_returns_default_for_new_profile(
        self, clean_profile_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """New profile gets default config (all filters off)."""
        result = load_profile("jonas")

        # Default config has all HMs disabled
        assert result is not None
        assert result.has_surf is False
        assert result.has_dive is False
        assert result.rod_level == "None"
        assert result.has_rock_smash is False
        assert result.post_game is False

    def test_load_profile_returns_saved_values(self, clean_profile_files: Path) -> None:
        """Loading a profile returns previously saved values."""
        # Save a config
        config = LocationFilterConfig(
            has_surf=True,
            has_dive=False,
            rod_level="Good Rod",
            has_rock_smash=True,
            post_game=False,
            level_cap=35,
        )
        save_profile("jonas", config)

        # Load it back
        result = load_profile("jonas")

        assert result is not None
        assert result.has_surf is True
        assert result.has_dive is False
        assert result.rod_level == "Good Rod"
        assert result.has_rock_smash is True
        assert result.post_game is False
        assert result.level_cap == 35


class TestSaveProfile:
    """Tests for save_profile function."""

    def test_save_profile_persists_data(self, clean_profile_files: Path) -> None:
        """Saved profile data persists across loads."""
        config = LocationFilterConfig(
            has_surf=True,
            has_dive=True,
            rod_level="Super Rod",
            has_rock_smash=True,
            post_game=True,
            level_cap=50,
        )

        save_profile("tim", config)

        # Load directly from file to verify persistence
        profiles_file = clean_profile_files / "game_profiles.json"
        with profiles_file.open() as f:
            data = json.load(f)

        assert data["profiles"]["tim"]["has_surf"] is True
        assert data["profiles"]["tim"]["level_cap"] == 50

    def test_save_profile_does_not_affect_other_profiles(self, clean_profile_files: Path) -> None:
        """Saving one profile doesn't change another profile's data."""
        config_jonas = LocationFilterConfig(has_surf=True, has_dive=False)
        config_tim = LocationFilterConfig(has_surf=False, has_dive=True)

        save_profile("jonas", config_jonas)
        save_profile("tim", config_tim)

        loaded_jonas = load_profile("jonas")
        loaded_tim = load_profile("tim")

        assert loaded_jonas is not None
        assert loaded_jonas.has_surf is True
        assert loaded_jonas.has_dive is False

        assert loaded_tim is not None
        assert loaded_tim.has_surf is False
        assert loaded_tim.has_dive is True


class TestActiveProfile:
    """Tests for get/set active profile functions."""

    def test_get_active_profile_returns_jonas_by_default(self, clean_profile_files: Path) -> None:
        """Default active profile is 'jonas'."""
        result = get_active_profile_name()

        assert result == "jonas"

    def test_set_active_profile_persists(self, clean_profile_files: Path) -> None:
        """Setting active profile persists the change."""
        set_active_profile("tim")

        result = get_active_profile_name()

        assert result == "tim"

    def test_set_active_profile_to_none(self, clean_profile_files: Path) -> None:
        """Setting active profile to None returns None on get."""
        set_active_profile(None)

        # Read raw file to verify None is stored
        profiles_file = clean_profile_files / "game_profiles.json"
        with profiles_file.open() as f:
            data = json.load(f)

        assert data["active_profile"] is None

    def test_get_active_profile_defaults_invalid_to_jonas(self, clean_profile_files: Path) -> None:
        """Invalid stored profile name defaults to 'jonas'."""
        # Manually write invalid profile
        profiles_file = clean_profile_files / "game_profiles.json"
        profiles_file.write_text('{"profiles": {}, "active_profile": "invalid"}')

        result = get_active_profile_name()

        assert result == "jonas"


class TestMigrateLegacyFile:
    """Tests for legacy file migration."""

    def test_migrate_legacy_file_copies_to_jonas(self, clean_profile_files: Path) -> None:
        """Legacy game_progress.json is migrated to jonas profile."""
        # Create legacy file with custom settings
        legacy_file = clean_profile_files / "game_progress.json"
        legacy_data = {
            "has_surf": True,
            "has_dive": True,
            "rod_level": "Good Rod",
            "has_rock_smash": False,
            "post_game": True,
            "level_cap": 45,
        }
        with legacy_file.open("w") as f:
            json.dump(legacy_data, f)

        # Trigger migration by loading a profile
        _migrate_legacy_file()

        # Verify migration
        jonas_config = load_profile("jonas")

        assert jonas_config is not None
        assert jonas_config.has_surf is True
        assert jonas_config.has_dive is True
        assert jonas_config.rod_level == "Good Rod"
        assert jonas_config.has_rock_smash is False
        assert jonas_config.post_game is True
        assert jonas_config.level_cap == 45

    def test_migrate_legacy_file_creates_tim_with_defaults(self, clean_profile_files: Path) -> None:
        """Migration creates tim profile with default (disabled) settings."""
        # Create legacy file
        legacy_file = clean_profile_files / "game_progress.json"
        with legacy_file.open("w") as f:
            json.dump({"has_surf": True}, f)

        # Trigger migration
        _migrate_legacy_file()

        # Verify tim has defaults
        tim_config = load_profile("tim")

        assert tim_config is not None
        assert tim_config.has_surf is False
        assert tim_config.has_dive is False
        assert tim_config.rod_level == "None"

    def test_migrate_skips_if_profiles_exist(self, clean_profile_files: Path) -> None:
        """Migration doesn't run if game_profiles.json already exists."""
        # Create existing profiles file
        profiles_file = clean_profile_files / "game_profiles.json"
        profiles_file.write_text('{"profiles": {"jonas": {"has_surf": false}}, "active_profile": "jonas"}')

        # Create legacy file that should be ignored
        legacy_file = clean_profile_files / "game_progress.json"
        with legacy_file.open("w") as f:
            json.dump({"has_surf": True}, f)

        # Trigger migration
        _migrate_legacy_file()

        # Verify profiles file wasn't changed
        jonas_config = load_profile("jonas")
        assert jonas_config is not None
        assert jonas_config.has_surf is False  # Original value, not migrated


class TestApplyLocationFiltersWithNone:
    """Tests for apply_location_filters with None config."""

    def test_apply_location_filters_with_none_returns_unchanged(self) -> None:
        """Passing None config returns the DataFrame unchanged."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Deep Sea"],
                "encounter_method": ["grass", "surfing"],
                "encounter_notes": ["", "Underwater"],
                "requirement": ["", "Beat the League"],
            }
        )

        result = apply_location_filters(df, None)

        # Should return the same DataFrame unchanged
        assert result.shape == df.shape
        assert result.equals(df)

    def test_apply_location_filters_with_config_filters_data(self) -> None:
        """Passing a config applies filters normally."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Deep Sea"],
                "encounter_method": ["grass", "surfing"],
                "encounter_notes": ["", "Underwater"],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_surf=False)

        result = apply_location_filters(df, config)

        # Surfing location should be filtered out
        assert len(result) == 1
        assert result["location_name"][0] == "Route 1"


class TestProfileNames:
    """Tests for profile name constants."""

    def test_profile_names_contains_jonas_and_tim(self) -> None:
        """PROFILE_NAMES contains exactly jonas and tim."""
        assert "jonas" in PROFILE_NAMES
        assert "tim" in PROFILE_NAMES
        assert len(PROFILE_NAMES) == 2
