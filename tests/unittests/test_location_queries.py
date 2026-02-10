# ABOUTME: Unit tests for the location query functions and filter logic.
# ABOUTME: Tests location search, Pokemon lookup, and filter application.

import sqlite3
from pathlib import Path

import pytest

from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters
from unbounddb.app.queries import (
    get_all_evolutions,
    get_all_pokemon_names_from_locations,
    get_available_pokemon_set,
    get_first_blocked_evolution,
    get_pre_evolutions,
    search_pokemon_locations,
)


class TestApplyLocationFiltersHasSurf:
    """Tests for the has_surf filter in apply_location_filters."""

    def test_excludes_surfing_when_no_surf(self) -> None:
        """When has_surf=False, surfing encounters should be excluded."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "surfing",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_surf=False)
        result = apply_location_filters(data, config)
        assert len(result) == 1
        assert [r["encounter_method"] for r in result] == ["grass"]

    def test_includes_surfing_when_has_surf(self) -> None:
        """When has_surf=True, surfing encounters should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "surfing",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_surf=True)
        result = apply_location_filters(data, config)
        assert len(result) == 2


class TestApplyLocationFiltersHasDive:
    """Tests for the has_dive filter in apply_location_filters."""

    def test_excludes_underwater_when_no_dive(self) -> None:
        """When has_dive=False, Underwater encounters should be excluded."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "surfing",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "surfing",
                "encounter_notes": "Underwater",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_dive=False)
        result = apply_location_filters(data, config)
        assert len(result) == 1
        assert "Underwater" not in [r["encounter_notes"] for r in result]

    def test_includes_underwater_when_has_dive(self) -> None:
        """When has_dive=True, Underwater encounters should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "surfing",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "surfing",
                "encounter_notes": "Underwater",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_dive=True)
        result = apply_location_filters(data, config)
        assert len(result) == 2


class TestApplyLocationFiltersRodLevel:
    """Tests for the rod_level filter in apply_location_filters."""

    @pytest.fixture
    def rod_df(self) -> list[dict[str, str]]:
        """List of dicts with all rod types and grass."""
        return [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 1",
                "encounter_method": "old_rod",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 1",
                "encounter_method": "good_rod",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 1",
                "encounter_method": "super_rod",
                "encounter_notes": "",
                "requirement": "",
            },
        ]

    def test_rod_none_excludes_all_rods(self, rod_df: list[dict[str, str]]) -> None:
        """When rod_level=None, all rod encounters should be excluded."""
        config = LocationFilterConfig(rod_level="None")
        result = apply_location_filters(rod_df, config)
        assert len(result) == 1
        assert [r["encounter_method"] for r in result] == ["grass"]

    def test_old_rod_excludes_good_and_super(self, rod_df: list[dict[str, str]]) -> None:
        """When rod_level=Old Rod, good_rod and super_rod should be excluded."""
        config = LocationFilterConfig(rod_level="Old Rod")
        result = apply_location_filters(rod_df, config)
        methods = [r["encounter_method"] for r in result]
        assert "grass" in methods
        assert "old_rod" in methods
        assert "good_rod" not in methods
        assert "super_rod" not in methods

    def test_good_rod_excludes_super(self, rod_df: list[dict[str, str]]) -> None:
        """When rod_level=Good Rod, super_rod should be excluded."""
        config = LocationFilterConfig(rod_level="Good Rod")
        result = apply_location_filters(rod_df, config)
        methods = [r["encounter_method"] for r in result]
        assert "grass" in methods
        assert "old_rod" in methods
        assert "good_rod" in methods
        assert "super_rod" not in methods

    def test_super_rod_includes_all(self, rod_df: list[dict[str, str]]) -> None:
        """When rod_level=Super Rod, all rods should be included."""
        config = LocationFilterConfig(rod_level="Super Rod")
        result = apply_location_filters(rod_df, config)
        methods = [r["encounter_method"] for r in result]
        assert len(methods) == 4


class TestApplyLocationFiltersRockSmash:
    """Tests for the has_rock_smash filter in apply_location_filters."""

    def test_excludes_rock_smash_when_disabled(self) -> None:
        """When has_rock_smash=False, rock_smash encounters should be excluded."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "rock_smash",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_rock_smash=False)
        result = apply_location_filters(data, config)
        assert len(result) == 1
        assert [r["encounter_method"] for r in result] == ["grass"]

    def test_includes_rock_smash_when_enabled(self) -> None:
        """When has_rock_smash=True, rock_smash encounters should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "rock_smash",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(has_rock_smash=True)
        result = apply_location_filters(data, config)
        assert len(result) == 2


class TestApplyLocationFiltersPostGame:
    """Tests for the post_game filter in apply_location_filters."""

    def test_excludes_post_game_locations_when_disabled(self) -> None:
        """When post_game=False, Post-game locations should be excluded."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Post-game Area",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(post_game=False)
        result = apply_location_filters(data, config)
        assert len(result) == 1
        assert [r["location_name"] for r in result] == ["Route 1"]

    def test_excludes_beat_the_league_requirement_when_disabled(self) -> None:
        """When post_game=False, Beat the League requirements should be excluded."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "Beat the League",
            },
        ]
        config = LocationFilterConfig(post_game=False)
        result = apply_location_filters(data, config)
        assert len(result) == 1
        assert [r["location_name"] for r in result] == ["Route 1"]

    def test_includes_post_game_when_enabled(self) -> None:
        """When post_game=True, Post-game locations should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Post-game Area",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "Beat the League",
            },
        ]
        config = LocationFilterConfig(post_game=True)
        result = apply_location_filters(data, config)
        assert len(result) == 2


class TestApplyLocationFiltersAccessible:
    """Tests for the accessible_locations filter in apply_location_filters."""

    def test_empty_list_includes_all_locations(self) -> None:
        """When accessible_locations is empty, all locations should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 3",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(accessible_locations=[])
        result = apply_location_filters(data, config)
        assert len(result) == 3

    def test_none_includes_all_locations(self) -> None:
        """When accessible_locations is None, all locations should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 3",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(accessible_locations=None)
        result = apply_location_filters(data, config)
        assert len(result) == 3

    def test_filters_to_only_selected_locations(self) -> None:
        """When accessible_locations is specified, only those should be included."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Route 3",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(accessible_locations=["Route 1", "Route 3"])
        result = apply_location_filters(data, config)
        assert len(result) == 2
        assert {r["location_name"] for r in result} == {"Route 1", "Route 3"}


class TestApplyLocationFiltersEmptyInput:
    """Tests for handling empty inputs."""

    def test_empty_dataframe_returns_empty(self) -> None:
        """Empty input list should return empty list."""
        data: list[dict[str, str]] = []
        config = LocationFilterConfig()
        result = apply_location_filters(data, config)
        assert not result
        assert result == []


class TestApplyLocationFiltersCombined:
    """Tests for combined filter application."""

    def test_multiple_filters_combine_correctly(self) -> None:
        """Multiple filters should combine with AND logic."""
        data = [
            {
                "location_name": "Route 1",
                "encounter_method": "surfing",
                "encounter_notes": "Underwater",
                "requirement": "",
            },
            {
                "location_name": "Route 2",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "",
            },
            {
                "location_name": "Post-game Area",
                "encounter_method": "grass",
                "encounter_notes": "",
                "requirement": "Beat the League",
            },
            {
                "location_name": "Route 3",
                "encounter_method": "super_rod",
                "encounter_notes": "",
                "requirement": "",
            },
        ]
        config = LocationFilterConfig(
            has_surf=True,  # Surfing included
            has_dive=False,  # But not underwater
            rod_level="Good Rod",  # No super rod
            has_rock_smash=True,
            post_game=False,  # No post-game
            accessible_locations=None,
        )
        result = apply_location_filters(data, config)
        # Route 1 excluded (underwater)
        # Route 2 included
        # Post-game Area excluded (post-game)
        # Route 3 excluded (super rod)
        assert len(result) == 1
        assert [r["location_name"] for r in result] == ["Route 2"]


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
        assert config.level_cap is None


class TestGetPreEvolutions:
    """Tests for the get_pre_evolutions function.

    Note: These tests require a database with the evolutions table.
    They use pytest fixtures to create a test database with evolution data.
    """

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        conn.commit()
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
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        conn.commit()
        conn.close()
        return db_path

    def test_search_locations_includes_pre_evolutions(self, test_db: Path) -> None:
        """Searching for Charizard should include Charmander locations."""
        result = search_pokemon_locations("Charizard", test_db)

        # Should find Charmander's locations when searching for Charizard
        assert len(result) == 2
        assert "Charmander" in [r["pokemon"] for r in result]
        assert "Mt. Ember" in [r["location_name"] for r in result]
        assert "Fire Path" in [r["location_name"] for r in result]

    def test_search_locations_returns_pokemon_column(self, test_db: Path) -> None:
        """Result should include pokemon column showing which Pokemon spawns."""
        result = search_pokemon_locations("Charizard", test_db)

        assert all("pokemon" in r for r in result)
        # All results should show Charmander since that's what actually spawns
        assert all(r["pokemon"] == "Charmander" for r in result)

    def test_search_locations_no_pre_evolutions(self, test_db: Path) -> None:
        """Pokemon with no pre-evolutions should only return its own locations."""
        result = search_pokemon_locations("Magikarp", test_db)

        assert len(result) == 1
        assert [r["pokemon"] for r in result] == ["Magikarp"]
        assert [r["location_name"] for r in result] == ["Route 1"]


class TestGetAllPokemonNamesFromLocations:
    """Tests for get_all_pokemon_names_from_locations including evolutions."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution and location data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        conn.commit()
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


class TestGetAllEvolutions:
    """Tests for the get_all_evolutions function.

    Tests evolution chain walking forward from a Pokemon.
    """

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        conn.commit()
        conn.close()
        return db_path

    def test_get_all_evolutions_single_stage(self, test_db: Path) -> None:
        """Test getting evolution for a single-stage evolution."""
        result = get_all_evolutions("Charmander", test_db)
        # Charmander evolves to Charmeleon, then Charmeleon evolves to Charizard
        assert len(result) == 2
        assert "Charmeleon" in result
        assert "Charizard" in result

    def test_get_all_evolutions_middle_stage(self, test_db: Path) -> None:
        """Test getting evolution from middle of chain."""
        result = get_all_evolutions("Charmeleon", test_db)
        # Charmeleon only evolves to Charizard
        assert result == ["Charizard"]

    def test_get_all_evolutions_no_evolution(self, test_db: Path) -> None:
        """Test getting evolutions for a Pokemon with no evolutions."""
        result = get_all_evolutions("Charizard", test_db)
        # Charizard has no further evolutions
        assert result == []

    def test_get_all_evolutions_case_insensitive(self, test_db: Path) -> None:
        """Test that search is case-insensitive."""
        result = get_all_evolutions("CHARMANDER", test_db)
        assert len(result) == 2
        assert "Charmeleon" in result
        assert "Charizard" in result

    def test_get_all_evolutions_unknown_pokemon(self, test_db: Path) -> None:
        """Test getting evolutions for unknown Pokemon."""
        result = get_all_evolutions("Ditto", test_db)
        assert result == []


class TestGetAvailablePokemonSet:
    """Tests for get_available_pokemon_set function."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution and location data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        # Insert location data
        conn.execute("""
            INSERT INTO locations VALUES
            ('Charmander', 'charmander', 'Mt. Ember', 'grass', '', ''),
            ('Magikarp', 'magikarp', 'Route 1', 'super_rod', '', ''),
            ('Tentacool', 'tentacool', 'Route 1', 'surfing', '', '')
        """)

        conn.commit()
        conn.close()
        return db_path

    def test_includes_directly_catchable_pokemon(self, test_db: Path) -> None:
        """Should include Pokemon that are directly catchable."""
        config = LocationFilterConfig()
        result = get_available_pokemon_set(config, test_db)

        assert "Charmander" in result
        assert "Magikarp" in result
        assert "Tentacool" in result

    def test_includes_evolutions_of_catchable_pokemon(self, test_db: Path) -> None:
        """Should include evolutions of catchable Pokemon."""
        config = LocationFilterConfig()
        result = get_available_pokemon_set(config, test_db)

        # Charmeleon and Charizard evolve from catchable Charmander
        assert "Charmeleon" in result
        assert "Charizard" in result

    def test_filters_by_surf(self, test_db: Path) -> None:
        """Should exclude surfing encounters when has_surf=False."""
        config = LocationFilterConfig(has_surf=False)
        result = get_available_pokemon_set(config, test_db)

        # Tentacool is only available via surfing
        assert "Tentacool" not in result
        # But Charmander and Magikarp should still be available
        assert "Charmander" in result
        assert "Magikarp" in result

    def test_filters_by_rod_level(self, test_db: Path) -> None:
        """Should exclude rod encounters based on rod_level."""
        config = LocationFilterConfig(rod_level="Good Rod")
        result = get_available_pokemon_set(config, test_db)

        # Magikarp requires super_rod which is excluded with Good Rod
        assert "Magikarp" not in result
        # But Charmander should still be available
        assert "Charmander" in result

    def test_returns_empty_set_when_no_matches(self, test_db: Path) -> None:
        """Should return empty set when no locations match filters."""
        config = LocationFilterConfig(
            has_surf=False,
            rod_level="None",
            accessible_locations=["Nonexistent Location"],
        )
        result = get_available_pokemon_set(config, test_db)

        assert result == set()


class TestGetAllEvolutionsWithLevelCap:
    """Tests for get_all_evolutions with level_cap parameter."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution data including levels."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        # Insert evolution chains with level data
        # Charmander -16-> Charmeleon -36-> Charizard (Level evolutions)
        # Pichu -Friendship-> Pikachu -Thunder Stone-> Raichu (Non-level evolutions)
        # Bulbasaur -16-> Ivysaur -32-> Venusaur
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard'),
            ('Pichu', 'Pikachu', 'Friendship', '', 'pichu', 'pikachu'),
            ('Pikachu', 'Raichu', 'Stone', 'Thunder Stone', 'pikachu', 'raichu'),
            ('Bulbasaur', 'Ivysaur', 'Level', '16', 'bulbasaur', 'ivysaur'),
            ('Ivysaur', 'Venusaur', 'Level', '32', 'ivysaur', 'venusaur')
        """)

        conn.commit()
        conn.close()
        return db_path

    def test_no_level_cap_returns_all_evolutions(self, test_db: Path) -> None:
        """Without level cap, should return all evolutions."""
        result = get_all_evolutions("Charmander", test_db, level_cap=None)
        assert len(result) == 2
        assert "Charmeleon" in result
        assert "Charizard" in result

    def test_level_cap_excludes_high_level_evolutions(self, test_db: Path) -> None:
        """Level cap should exclude evolutions requiring higher levels."""
        # Level cap 20 should include Charmeleon (16) but exclude Charizard (36)
        result = get_all_evolutions("Charmander", test_db, level_cap=20)
        assert "Charmeleon" in result
        assert "Charizard" not in result

    def test_level_cap_includes_at_exact_level(self, test_db: Path) -> None:
        """Evolution should be included if level cap equals evolution level."""
        result = get_all_evolutions("Charmander", test_db, level_cap=16)
        assert "Charmeleon" in result

    def test_level_cap_excludes_at_one_below(self, test_db: Path) -> None:
        """Evolution should be excluded if level cap is below evolution level."""
        result = get_all_evolutions("Charmander", test_db, level_cap=15)
        assert "Charmeleon" not in result

    def test_non_level_evolutions_always_included(self, test_db: Path) -> None:
        """Non-level evolutions (Stone, Friendship) should always be included."""
        # Pichu evolves to Pikachu via Friendship, Pikachu evolves to Raichu via Stone
        result = get_all_evolutions("Pichu", test_db, level_cap=1)
        assert "Pikachu" in result
        assert "Raichu" in result

    def test_level_cap_chain_stops_at_high_level(self, test_db: Path) -> None:
        """If middle evolution is blocked, further evolutions should also be blocked."""
        # Bulbasaur -16-> Ivysaur -32-> Venusaur
        # Level cap 20 blocks Venusaur (needs 32)
        result = get_all_evolutions("Bulbasaur", test_db, level_cap=20)
        assert "Ivysaur" in result
        assert "Venusaur" not in result


class TestGetAvailablePokemonSetWithLevelCap:
    """Tests for get_available_pokemon_set with level_cap filter."""

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution and location data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        # Charmander -16-> Charmeleon -36-> Charizard
        # Eevee -Stone-> Vaporeon (non-level)
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard'),
            ('Eevee', 'Vaporeon', 'Stone', 'Water Stone', 'eevee', 'vaporeon')
        """)

        conn.execute("""
            INSERT INTO locations VALUES
            ('Charmander', 'charmander', 'Mt. Ember', 'grass', '', ''),
            ('Eevee', 'eevee', 'Route 1', 'grass', '', '')
        """)

        conn.commit()
        conn.close()
        return db_path

    def test_level_cap_filters_high_level_evolutions(self, test_db: Path) -> None:
        """Level cap should exclude Pokemon requiring evolution above that level."""
        config = LocationFilterConfig(level_cap=20)
        result = get_available_pokemon_set(config, test_db)

        assert "Charmander" in result
        assert "Charmeleon" in result  # Evolves at 16
        assert "Charizard" not in result  # Evolves at 36

    def test_level_cap_allows_non_level_evolutions(self, test_db: Path) -> None:
        """Non-level evolutions should be included regardless of level cap."""
        config = LocationFilterConfig(level_cap=1)
        result = get_available_pokemon_set(config, test_db)

        # Eevee evolves via Stone, not level
        assert "Eevee" in result
        assert "Vaporeon" in result

    def test_no_level_cap_includes_all_evolutions(self, test_db: Path) -> None:
        """Without level cap, all evolutions should be included."""
        config = LocationFilterConfig(level_cap=None)
        result = get_available_pokemon_set(config, test_db)

        assert "Charmander" in result
        assert "Charmeleon" in result
        assert "Charizard" in result
        assert "Eevee" in result
        assert "Vaporeon" in result


class TestGetFirstBlockedEvolution:
    """Tests for the get_first_blocked_evolution function.

    Walks backward from an evolved Pokemon and finds the first evolution
    step blocked by the level cap.
    """

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> Path:
        """Create a test database with evolution data."""
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))

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

        # Charmander -16-> Charmeleon -36-> Charizard (Level evolutions)
        # Pichu -Friendship-> Pikachu -Stone-> Raichu (Non-level evolutions)
        # Snover -40-> Abomasnow (single Level evolution)
        conn.execute("""
            INSERT INTO evolutions VALUES
            ('Charmander', 'Charmeleon', 'Level', '16', 'charmander', 'charmeleon'),
            ('Charmeleon', 'Charizard', 'Level', '36', 'charmeleon', 'charizard'),
            ('Pichu', 'Pikachu', 'Friendship', '', 'pichu', 'pikachu'),
            ('Pikachu', 'Raichu', 'Stone', 'Thunder Stone', 'pikachu', 'raichu'),
            ('Snover', 'Abomasnow', 'Level', '40', 'snover', 'abomasnow')
        """)

        conn.commit()
        conn.close()
        return db_path

    def test_blocked_evolution_returns_block_info(self, test_db: Path) -> None:
        """Should return block info when evolution is blocked by level cap."""
        result = get_first_blocked_evolution("Abomasnow", level_cap=36, db_path=test_db)

        assert result is not None
        assert result["from_pokemon"] == "Snover"
        assert result["to_pokemon"] == "Abomasnow"
        assert result["level"] == 40

    def test_no_block_when_cap_high_enough(self, test_db: Path) -> None:
        """Should return None when level cap is high enough."""
        result = get_first_blocked_evolution("Abomasnow", level_cap=40, db_path=test_db)

        assert result is None

    def test_no_evolutions_returns_none(self, test_db: Path) -> None:
        """Should return None for Pokemon with no evolutions."""
        result = get_first_blocked_evolution("Pikachu", level_cap=10, db_path=test_db)

        # Pikachu evolves from Pichu via Friendship (non-level), so no block
        assert result is None

    def test_unknown_pokemon_returns_none(self, test_db: Path) -> None:
        """Should return None for unknown Pokemon."""
        result = get_first_blocked_evolution("Ditto", level_cap=10, db_path=test_db)

        assert result is None

    def test_multi_step_chain_returns_first_blocked(self, test_db: Path) -> None:
        """Should return the first blocked step from the base form."""
        # Charmander -16-> Charmeleon -36-> Charizard
        # With cap 15, Charmeleon (16) is blocked — that's closest to base
        result = get_first_blocked_evolution("Charizard", level_cap=15, db_path=test_db)

        assert result is not None
        assert result["from_pokemon"] == "Charmander"
        assert result["to_pokemon"] == "Charmeleon"
        assert result["level"] == 16

    def test_multi_step_chain_later_step_blocked(self, test_db: Path) -> None:
        """When only the later step is blocked, should return that step."""
        # Charmander -16-> Charmeleon -36-> Charizard
        # With cap 20, only Charizard (36) is blocked
        result = get_first_blocked_evolution("Charizard", level_cap=20, db_path=test_db)

        assert result is not None
        assert result["from_pokemon"] == "Charmeleon"
        assert result["to_pokemon"] == "Charizard"
        assert result["level"] == 36
