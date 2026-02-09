# ABOUTME: Tests for multi-profile game progress persistence with progression computation.
# ABOUTME: Verifies profile loading, saving, and LocationFilterConfig computation from progression data.

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
    save_profile_progress,
    set_active_profile,
)
from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters
from unbounddb.progression.progression_data import ProgressionEntry, load_progression


def _make_test_entries() -> tuple[ProgressionEntry, ...]:
    """Create a small test progression for monkeypatching."""
    return (
        ProgressionEntry(
            step=0,
            trainer_name=None,
            trainer_key=None,
            battle_type=None,
            badge_number=0,
            locations=["Route 1"],
            hm_unlocks=[],
            level_cap_vanilla=15,
            level_cap_difficult=20,
            post_game=False,
        ),
        ProgressionEntry(
            step=1,
            trainer_name="Leader Mirskle",
            trainer_key="leader_mirskle",
            battle_type="GYM",
            badge_number=1,
            locations=["Route 2", "Route 3"],
            hm_unlocks=["Surf"],
            level_cap_vanilla=22,
            level_cap_difficult=26,
            post_game=False,
        ),
        ProgressionEntry(
            step=2,
            trainer_name="Post Boss",
            trainer_key="post_boss",
            battle_type="BOSS",
            badge_number=None,
            locations=["Rift Cave"],
            hm_unlocks=["Dive"],
            post_game=True,
        ),
    )


@pytest.fixture
def clean_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a clean temporary database and patch path + progression data."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = db_dir / "user_data.duckdb"

    # Patch the user_db_path function
    monkeypatch.setattr(user_database, "_get_user_db_path", lambda: db_path)

    # Patch load_progression to return test data
    load_progression.cache_clear()
    monkeypatch.setattr(
        "unbounddb.app.game_progress_persistence.load_progression",
        _make_test_entries,
    )

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
        """New profile at step 0 has only step 0 locations and no HMs."""
        create_new_profile("jonas")
        config, _difficulty = load_profile("jonas")

        assert config is not None
        assert config.has_surf is False
        assert config.has_dive is False
        assert config.has_rock_smash is False
        assert config.post_game is False
        assert config.accessible_locations == ["Route 1"]
        assert config.level_cap == 15

    def test_load_profile_at_step_1_has_surf(self, clean_db: Path) -> None:
        """Profile at step 1 (after gym leader) has surf and accumulated locations."""
        create_new_profile("jonas")
        save_profile_progress("jonas", progression_step=1, rod_level="None")

        config, _difficulty = load_profile("jonas")

        assert config is not None
        assert config.has_surf is True
        assert config.accessible_locations == ["Route 1", "Route 2", "Route 3"]
        assert config.level_cap == 22

    def test_load_profile_difficult_uses_difficult_cap(self, clean_db: Path) -> None:
        """Profile with Expert difficulty uses difficult level cap."""
        create_new_profile("jonas")
        save_profile_progress("jonas", progression_step=1, rod_level="None", difficulty="Expert")

        config, difficulty = load_profile("jonas")

        assert config is not None
        assert config.level_cap == 26
        assert difficulty == "Expert"

    def test_load_nonexistent_profile_returns_default(self, clean_db: Path) -> None:
        """Loading nonexistent profile returns default config."""
        config, difficulty = load_profile("nonexistent")

        assert config is not None
        assert difficulty is None

    def test_load_profile_rod_level_passed_through(self, clean_db: Path) -> None:
        """Rod level from profile is passed through to config."""
        create_new_profile("jonas")
        save_profile_progress("jonas", progression_step=0, rod_level="Good Rod")

        config, _difficulty = load_profile("jonas")

        assert config is not None
        assert config.rod_level == "Good Rod"


class TestSaveProfileProgress:
    """Tests for save_profile_progress function."""

    def test_save_profile_persists_data(self, clean_db: Path) -> None:
        """Saved profile data persists across loads."""
        create_new_profile("tim")
        save_profile_progress("tim", progression_step=2, rod_level="Super Rod", difficulty="Veteran")

        # Load and verify
        config, loaded_difficulty = load_profile("tim")

        assert config is not None
        assert config.post_game is True
        assert config.has_dive is True
        assert config.rod_level == "Super Rod"
        assert loaded_difficulty == "Veteran"

    def test_save_profile_does_not_affect_other_profiles(self, clean_db: Path) -> None:
        """Saving one profile doesn't change another profile's data."""
        create_new_profile("jonas")
        create_new_profile("tim")

        save_profile_progress("jonas", progression_step=1, rod_level="None")
        save_profile_progress("tim", progression_step=0, rod_level="Old Rod")

        config_jonas, _ = load_profile("jonas")
        config_tim, _ = load_profile("tim")

        assert config_jonas is not None
        assert config_jonas.has_surf is True  # step 1 has Surf
        assert config_jonas.rod_level == "None"

        assert config_tim is not None
        assert config_tim.has_surf is False  # step 0 has no Surf
        assert config_tim.rod_level == "Old Rod"


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
