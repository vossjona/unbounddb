# ABOUTME: Unit tests for the location query functions and filter logic.
# ABOUTME: Tests location search, Pokemon lookup, and filter application.

import polars as pl
import pytest

from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters


class TestApplyLocationFiltersHasSurf:
    """Tests for the has_surf filter in apply_location_filters."""

    def test_excludes_surfing_when_no_surf(self) -> None:
        """When has_surf=False, surfing encounters should be excluded."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["grass", "surfing"],
                "encounter_notes": ["", ""],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_surf=False)
        result = apply_location_filters(df, config)
        assert len(result) == 1
        assert result["encounter_method"].to_list() == ["grass"]

    def test_includes_surfing_when_has_surf(self) -> None:
        """When has_surf=True, surfing encounters should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["grass", "surfing"],
                "encounter_notes": ["", ""],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_surf=True)
        result = apply_location_filters(df, config)
        assert len(result) == 2


class TestApplyLocationFiltersHasDive:
    """Tests for the has_dive filter in apply_location_filters."""

    def test_excludes_underwater_when_no_dive(self) -> None:
        """When has_dive=False, Underwater encounters should be excluded."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["surfing", "surfing"],
                "encounter_notes": ["", "Underwater"],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_dive=False)
        result = apply_location_filters(df, config)
        assert len(result) == 1
        assert "Underwater" not in result["encounter_notes"].to_list()

    def test_includes_underwater_when_has_dive(self) -> None:
        """When has_dive=True, Underwater encounters should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["surfing", "surfing"],
                "encounter_notes": ["", "Underwater"],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_dive=True)
        result = apply_location_filters(df, config)
        assert len(result) == 2


class TestApplyLocationFiltersRodLevel:
    """Tests for the rod_level filter in apply_location_filters."""

    @pytest.fixture
    def rod_df(self) -> pl.DataFrame:
        """DataFrame with all rod types and grass."""
        return pl.DataFrame(
            {
                "location_name": ["Route 1"] * 4,
                "encounter_method": ["grass", "old_rod", "good_rod", "super_rod"],
                "encounter_notes": ["", "", "", ""],
                "requirement": ["", "", "", ""],
            }
        )

    def test_rod_none_excludes_all_rods(self, rod_df: pl.DataFrame) -> None:
        """When rod_level=None, all rod encounters should be excluded."""
        config = LocationFilterConfig(rod_level="None")
        result = apply_location_filters(rod_df, config)
        assert len(result) == 1
        assert result["encounter_method"].to_list() == ["grass"]

    def test_old_rod_excludes_good_and_super(self, rod_df: pl.DataFrame) -> None:
        """When rod_level=Old Rod, good_rod and super_rod should be excluded."""
        config = LocationFilterConfig(rod_level="Old Rod")
        result = apply_location_filters(rod_df, config)
        methods = result["encounter_method"].to_list()
        assert "grass" in methods
        assert "old_rod" in methods
        assert "good_rod" not in methods
        assert "super_rod" not in methods

    def test_good_rod_excludes_super(self, rod_df: pl.DataFrame) -> None:
        """When rod_level=Good Rod, super_rod should be excluded."""
        config = LocationFilterConfig(rod_level="Good Rod")
        result = apply_location_filters(rod_df, config)
        methods = result["encounter_method"].to_list()
        assert "grass" in methods
        assert "old_rod" in methods
        assert "good_rod" in methods
        assert "super_rod" not in methods

    def test_super_rod_includes_all(self, rod_df: pl.DataFrame) -> None:
        """When rod_level=Super Rod, all rods should be included."""
        config = LocationFilterConfig(rod_level="Super Rod")
        result = apply_location_filters(rod_df, config)
        methods = result["encounter_method"].to_list()
        assert len(methods) == 4


class TestApplyLocationFiltersRockSmash:
    """Tests for the has_rock_smash filter in apply_location_filters."""

    def test_excludes_rock_smash_when_disabled(self) -> None:
        """When has_rock_smash=False, rock_smash encounters should be excluded."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["grass", "rock_smash"],
                "encounter_notes": ["", ""],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_rock_smash=False)
        result = apply_location_filters(df, config)
        assert len(result) == 1
        assert result["encounter_method"].to_list() == ["grass"]

    def test_includes_rock_smash_when_enabled(self) -> None:
        """When has_rock_smash=True, rock_smash encounters should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["grass", "rock_smash"],
                "encounter_notes": ["", ""],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(has_rock_smash=True)
        result = apply_location_filters(df, config)
        assert len(result) == 2


class TestApplyLocationFiltersPostGame:
    """Tests for the post_game filter in apply_location_filters."""

    def test_excludes_post_game_locations_when_disabled(self) -> None:
        """When post_game=False, Post-game locations should be excluded."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Post-game Area"],
                "encounter_method": ["grass", "grass"],
                "encounter_notes": ["", ""],
                "requirement": ["", ""],
            }
        )
        config = LocationFilterConfig(post_game=False)
        result = apply_location_filters(df, config)
        assert len(result) == 1
        assert result["location_name"].to_list() == ["Route 1"]

    def test_excludes_beat_the_league_requirement_when_disabled(self) -> None:
        """When post_game=False, Beat the League requirements should be excluded."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2"],
                "encounter_method": ["grass", "grass"],
                "encounter_notes": ["", ""],
                "requirement": ["", "Beat the League"],
            }
        )
        config = LocationFilterConfig(post_game=False)
        result = apply_location_filters(df, config)
        assert len(result) == 1
        assert result["location_name"].to_list() == ["Route 1"]

    def test_includes_post_game_when_enabled(self) -> None:
        """When post_game=True, Post-game locations should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Post-game Area"],
                "encounter_method": ["grass", "grass"],
                "encounter_notes": ["", ""],
                "requirement": ["", "Beat the League"],
            }
        )
        config = LocationFilterConfig(post_game=True)
        result = apply_location_filters(df, config)
        assert len(result) == 2


class TestApplyLocationFiltersAccessible:
    """Tests for the accessible_locations filter in apply_location_filters."""

    def test_empty_list_includes_all_locations(self) -> None:
        """When accessible_locations is empty, all locations should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2", "Route 3"],
                "encounter_method": ["grass", "grass", "grass"],
                "encounter_notes": ["", "", ""],
                "requirement": ["", "", ""],
            }
        )
        config = LocationFilterConfig(accessible_locations=[])
        result = apply_location_filters(df, config)
        assert len(result) == 3

    def test_none_includes_all_locations(self) -> None:
        """When accessible_locations is None, all locations should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2", "Route 3"],
                "encounter_method": ["grass", "grass", "grass"],
                "encounter_notes": ["", "", ""],
                "requirement": ["", "", ""],
            }
        )
        config = LocationFilterConfig(accessible_locations=None)
        result = apply_location_filters(df, config)
        assert len(result) == 3

    def test_filters_to_only_selected_locations(self) -> None:
        """When accessible_locations is specified, only those should be included."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2", "Route 3"],
                "encounter_method": ["grass", "grass", "grass"],
                "encounter_notes": ["", "", ""],
                "requirement": ["", "", ""],
            }
        )
        config = LocationFilterConfig(accessible_locations=["Route 1", "Route 3"])
        result = apply_location_filters(df, config)
        assert len(result) == 2
        assert set(result["location_name"].to_list()) == {"Route 1", "Route 3"}


class TestApplyLocationFiltersEmptyInput:
    """Tests for handling empty inputs."""

    def test_empty_dataframe_returns_empty(self) -> None:
        """Empty input DataFrame should return empty DataFrame."""
        df = pl.DataFrame(
            schema={
                "location_name": pl.String,
                "encounter_method": pl.String,
                "encounter_notes": pl.String,
                "requirement": pl.String,
            }
        )
        config = LocationFilterConfig()
        result = apply_location_filters(df, config)
        assert result.is_empty()
        assert list(result.columns) == ["location_name", "encounter_method", "encounter_notes", "requirement"]


class TestApplyLocationFiltersCombined:
    """Tests for combined filter application."""

    def test_multiple_filters_combine_correctly(self) -> None:
        """Multiple filters should combine with AND logic."""
        df = pl.DataFrame(
            {
                "location_name": ["Route 1", "Route 2", "Post-game Area", "Route 3"],
                "encounter_method": ["surfing", "grass", "grass", "super_rod"],
                "encounter_notes": ["Underwater", "", "", ""],
                "requirement": ["", "", "Beat the League", ""],
            }
        )
        config = LocationFilterConfig(
            has_surf=True,  # Surfing included
            has_dive=False,  # But not underwater
            rod_level="Good Rod",  # No super rod
            has_rock_smash=True,
            post_game=False,  # No post-game
            accessible_locations=None,
        )
        result = apply_location_filters(df, config)
        # Route 1 excluded (underwater)
        # Route 2 included
        # Post-game Area excluded (post-game)
        # Route 3 excluded (super rod)
        assert len(result) == 1
        assert result["location_name"].to_list() == ["Route 2"]


class TestLocationFilterConfigDefaults:
    """Tests for LocationFilterConfig default values."""

    def test_default_values_include_everything(self) -> None:
        """Default config should include all encounters."""
        config = LocationFilterConfig()
        assert config.has_surf is True
        assert config.has_dive is True
        assert config.rod_level == "Super Rod"
        assert config.has_rock_smash is True
        assert config.post_game is True
        assert config.accessible_locations is None
