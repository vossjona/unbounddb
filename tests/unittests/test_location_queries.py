# ABOUTME: Unit tests for the location query functions and filter logic.
# ABOUTME: Tests location search, Pokemon lookup, and filter application.

from pathlib import Path

import duckdb
import polars as pl
import pytest

from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters
from unbounddb.app.queries import (
    get_all_pokemon_names_from_locations,
    get_pre_evolutions,
    search_pokemon_locations,
)


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
                "pokemon": pl.String,
                "location_name": pl.String,
                "encounter_method": pl.String,
                "encounter_notes": pl.String,
                "requirement": pl.String,
            }
        )
        config = LocationFilterConfig()
        result = apply_location_filters(df, config)
        assert result.is_empty()
        assert list(result.columns) == [
            "pokemon",
            "location_name",
            "encounter_method",
            "encounter_notes",
            "requirement",
        ]


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


class TestGetPreEvolutions:
    """Tests for the get_pre_evolutions function.

    Note: These tests require a database with the evolutions table.
    They use pytest fixtures to create a test database with evolution data.
    """

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution data."""
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create evolutions table with test data
        conn.execute("""
            CREATE TABLE evolutions (
                from_pokemon VARCHAR,
                to_pokemon VARCHAR,
                method VARCHAR,
                condition VARCHAR,
                from_pokemon_key VARCHAR,
                to_pokemon_key VARCHAR
            )
        """)

        # Insert test evolution chains
        # Charmander -> Charmeleon -> Charizard
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard'),
            ('Pichu', 'Pikachu', 'Friendship', '', 'pichu', 'pikachu'),
            ('Pikachu', 'Raichu', 'Stone', 'Thunder Stone', 'pikachu', 'raichu'),
            ('Bulbasaur', 'Ivysaur', 'Level', '16', 'bulbasaur', 'ivysaur'),
            ('Ivysaur', 'Venusaur', 'Level', '32', 'ivysaur', 'venusaur')
        """)

        conn.close()
        return db_path

    def test_get_pre_evolutions_single_stage(self, test_db: Path) -> None:
        """Test getting pre-evolution for a single-stage evolution."""
        result = get_pre_evolutions("Charmeleon", test_db)
        assert result == ["Charmander"]

    def test_get_pre_evolutions_two_stage(self, test_db: Path) -> None:
        """Test getting pre-evolutions for a two-stage evolution chain."""
        result = get_pre_evolutions("Charizard", test_db)
        # Should return both Charmeleon and Charmander
        assert len(result) == 2
        assert "Charmeleon" in result
        assert "Charmander" in result

    def test_get_pre_evolutions_no_preevo(self, test_db: Path) -> None:
        """Test getting pre-evolutions for a Pokemon with no pre-evolutions."""
        result = get_pre_evolutions("Charmander", test_db)
        assert result == []

    def test_get_pre_evolutions_case_insensitive(self, test_db: Path) -> None:
        """Test that search is case-insensitive."""
        result = get_pre_evolutions("CHARIZARD", test_db)
        assert len(result) == 2
        assert "Charmeleon" in result
        assert "Charmander" in result


class TestSearchPokemonLocationsWithPreEvolutions:
    """Tests for search_pokemon_locations including pre-evolution locations."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution and location data."""
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create evolutions table
        conn.execute("""
            CREATE TABLE evolutions (
                from_pokemon VARCHAR,
                to_pokemon VARCHAR,
                method VARCHAR,
                condition VARCHAR,
                from_pokemon_key VARCHAR,
                to_pokemon_key VARCHAR
            )
        """)

        # Create locations table
        conn.execute("""
            CREATE TABLE locations (
                pokemon VARCHAR,
                pokemon_key VARCHAR,
                location_name VARCHAR,
                encounter_method VARCHAR,
                encounter_notes VARCHAR,
                requirement VARCHAR
            )
        """)

        # Insert evolution chain: Charmander -> Charmeleon -> Charizard
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard')
        """)

        # Insert location data - Charmander is catchable, Charizard is not
        conn.execute("""
            INSERT INTO locations VALUES
            ('Charmander', 'charmander', 'Mt. Ember', 'grass', '', ''),
            ('Charmander', 'charmander', 'Fire Path', 'cave', '', 'Beat the League'),
            ('Magikarp', 'magikarp', 'Route 1', 'old_rod', '', '')
        """)

        conn.close()
        return db_path

    def test_search_locations_includes_pre_evolutions(self, test_db: Path) -> None:
        """Searching for Charizard should include Charmander locations."""
        result = search_pokemon_locations("Charizard", test_db)

        # Should find Charmander's locations when searching for Charizard
        assert len(result) == 2
        assert "Charmander" in result["pokemon"].to_list()
        assert "Mt. Ember" in result["location_name"].to_list()
        assert "Fire Path" in result["location_name"].to_list()

    def test_search_locations_returns_pokemon_column(self, test_db: Path) -> None:
        """Result should include pokemon column showing which Pokemon spawns."""
        result = search_pokemon_locations("Charizard", test_db)

        assert "pokemon" in result.columns
        # All results should show Charmander since that's what actually spawns
        assert all(p == "Charmander" for p in result["pokemon"].to_list())

    def test_search_locations_no_pre_evolutions(self, test_db: Path) -> None:
        """Pokemon with no pre-evolutions should only return its own locations."""
        result = search_pokemon_locations("Magikarp", test_db)

        assert len(result) == 1
        assert result["pokemon"].to_list() == ["Magikarp"]
        assert result["location_name"].to_list() == ["Route 1"]


class TestGetAllPokemonNamesFromLocations:
    """Tests for get_all_pokemon_names_from_locations including evolutions."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution and location data."""
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create evolutions table
        conn.execute("""
            CREATE TABLE evolutions (
                from_pokemon VARCHAR,
                to_pokemon VARCHAR,
                method VARCHAR,
                condition VARCHAR,
                from_pokemon_key VARCHAR,
                to_pokemon_key VARCHAR
            )
        """)

        # Create locations table
        conn.execute("""
            CREATE TABLE locations (
                pokemon VARCHAR,
                pokemon_key VARCHAR,
                location_name VARCHAR,
                encounter_method VARCHAR,
                encounter_notes VARCHAR,
                requirement VARCHAR
            )
        """)

        # Insert evolution chain: Charmander -> Charmeleon -> Charizard
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard')
        """)

        # Insert location data - only Charmander is directly catchable
        conn.execute("""
            INSERT INTO locations VALUES
            ('Charmander', 'charmander', 'Mt. Ember', 'grass', '', ''),
            ('Magikarp', 'magikarp', 'Route 1', 'old_rod', '', '')
        """)

        conn.close()
        return db_path

    def test_includes_directly_catchable_pokemon(self, test_db: Path) -> None:
        """Should include Pokemon that are directly in the locations table."""
        result = get_all_pokemon_names_from_locations(test_db)

        assert "Charmander" in result
        assert "Magikarp" in result

    def test_includes_evolutions_of_catchable_pokemon(self, test_db: Path) -> None:
        """Should include evolutions of catchable Pokemon."""
        result = get_all_pokemon_names_from_locations(test_db)

        # Charmeleon and Charizard evolve from catchable Charmander
        assert "Charmeleon" in result
        assert "Charizard" in result

    def test_returns_sorted_list(self, test_db: Path) -> None:
        """Should return Pokemon names in sorted order."""
        result = get_all_pokemon_names_from_locations(test_db)

        assert result == sorted(result)
