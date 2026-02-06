# ABOUTME: Tests for multi-profile game progress persistence.
# ABOUTME: Verifies profile loading, saving, and None config handling.

from pathlib import Path

import polars as pl
import pytest

from unbounddb.app import user_database
from unbounddb.app.game_progress_persistence import (
    create_new_profile,
    delete_profile_by_name,
    get_active_profile_name,
    get_all_profile_names,
    load_profile,
    save_profile,
    set_active_profile,
)
from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters


@pytest.fixture
def clean_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a clean temporary database and patch path."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = db_dir / "user_data.duckdb"

    # Patch the user_db_path function
    monkeypatch.setattr(user_database, "_get_user_db_path", lambda: db_path)

    return db_path


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_profile_returns_none_tuple_for_none_input(self, clean_db: Path) -> None:
        """Loading profile with None returns (None, None)."""
        config, difficulty = load_profile(None)

        assert config is None
        assert difficulty is None

    def test_load_profile_returns_config_for_named_profile(self, clean_db: Path) -> None:
        """Loading a named profile returns LocationFilterConfig."""
        create_new_profile("jonas")
        config, _difficulty = load_profile("jonas")

        assert isinstance(config, LocationFilterConfig)

    def test_load_profile_returns_default_for_new_profile(self, clean_db: Path) -> None:
        """New profile gets default config (all filters off)."""
        create_new_profile("jonas")
        config, _difficulty = load_profile("jonas")

        # Default config has all HMs disabled
        assert config is not None
        assert config.has_surf is False
        assert config.has_dive is False
        assert config.rod_level == "None"
        assert config.has_rock_smash is False
        assert config.post_game is False

    def test_load_profile_returns_saved_values(self, clean_db: Path) -> None:
        """Loading a profile returns previously saved values."""
        create_new_profile("jonas")

        # Save a config
        config = LocationFilterConfig(
            has_surf=True,
            has_dive=False,
            rod_level="Good Rod",
            has_rock_smash=True,
            post_game=False,
            level_cap=35,
        )
        save_profile("jonas", config, difficulty="Expert")

        # Load it back
        loaded_config, loaded_difficulty = load_profile("jonas")

        assert loaded_config is not None
        assert loaded_config.has_surf is True
        assert loaded_config.has_dive is False
        assert loaded_config.rod_level == "Good Rod"
        assert loaded_config.has_rock_smash is True
        assert loaded_config.post_game is False
        assert loaded_config.level_cap == 35
        assert loaded_difficulty == "Expert"

    def test_load_nonexistent_profile_returns_default(self, clean_db: Path) -> None:
        """Loading nonexistent profile returns default config."""
        config, difficulty = load_profile("nonexistent")

        assert config is not None
        assert config.has_surf is False
        assert difficulty is None


class TestSaveProfile:
    """Tests for save_profile function."""

    def test_save_profile_persists_data(self, clean_db: Path) -> None:
        """Saved profile data persists across loads."""
        create_new_profile("tim")

        config = LocationFilterConfig(
            has_surf=True,
            has_dive=True,
            rod_level="Super Rod",
            has_rock_smash=True,
            post_game=True,
            level_cap=50,
        )

        save_profile("tim", config, difficulty="Veteran")

        # Load and verify
        loaded_config, loaded_difficulty = load_profile("tim")

        assert loaded_config is not None
        assert loaded_config.has_surf is True
        assert loaded_config.level_cap == 50
        assert loaded_difficulty == "Veteran"

    def test_save_profile_does_not_affect_other_profiles(self, clean_db: Path) -> None:
        """Saving one profile doesn't change another profile's data."""
        create_new_profile("jonas")
        create_new_profile("tim")

        config_jonas = LocationFilterConfig(has_surf=True, has_dive=False)
        config_tim = LocationFilterConfig(has_surf=False, has_dive=True)

        save_profile("jonas", config_jonas)
        save_profile("tim", config_tim)

        loaded_jonas, _ = load_profile("jonas")
        loaded_tim, _ = load_profile("tim")

        assert loaded_jonas is not None
        assert loaded_jonas.has_surf is True
        assert loaded_jonas.has_dive is False

        assert loaded_tim is not None
        assert loaded_tim.has_surf is False
        assert loaded_tim.has_dive is True


class TestActiveProfile:
    """Tests for get/set active profile functions."""

    def test_get_active_profile_returns_none_by_default(self, clean_db: Path) -> None:
        """Default active profile is None."""
        create_new_profile("jonas")
        result = get_active_profile_name()

        assert result is None

    def test_set_active_profile_persists(self, clean_db: Path) -> None:
        """Setting active profile persists the change."""
        create_new_profile("jonas")
        create_new_profile("tim")

        set_active_profile("tim")

        result = get_active_profile_name()

        assert result == "tim"

    def test_set_active_profile_to_none(self, clean_db: Path) -> None:
        """Setting active profile to None clears it."""
        create_new_profile("jonas")
        set_active_profile("jonas")
        set_active_profile(None)

        result = get_active_profile_name()

        assert result is None


class TestDynamicProfiles:
    """Tests for dynamic profile creation and deletion."""

    def test_get_all_profile_names_returns_sorted(self, clean_db: Path) -> None:
        """Profile names are returned sorted."""
        create_new_profile("tim")
        create_new_profile("alice")
        create_new_profile("jonas")

        names = get_all_profile_names()

        assert names == ["alice", "jonas", "tim"]

    def test_create_new_profile_returns_true(self, clean_db: Path) -> None:
        """Creating a new profile returns True."""
        result = create_new_profile("jonas")

        assert result is True

    def test_create_duplicate_profile_returns_false(self, clean_db: Path) -> None:
        """Creating duplicate profile returns False."""
        create_new_profile("jonas")
        result = create_new_profile("jonas")

        assert result is False

    def test_delete_profile_removes_it(self, clean_db: Path) -> None:
        """Deleting a profile removes it from the list."""
        create_new_profile("jonas")
        create_new_profile("tim")

        delete_profile_by_name("jonas")

        names = get_all_profile_names()

        assert "jonas" not in names
        assert "tim" in names

    def test_delete_nonexistent_profile_returns_false(self, clean_db: Path) -> None:
        """Deleting nonexistent profile returns False."""
        result = delete_profile_by_name("nonexistent")

        assert result is False


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
