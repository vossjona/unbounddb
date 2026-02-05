"""ABOUTME: Tests for location parsing from multiple CSV formats.
ABOUTME: Verifies Grass/Cave, Surfing/Fishing, and Gift/Static CSV parsing."""

import tempfile
from pathlib import Path

import pytest

from unbounddb.ingestion.locations_parser import (
    _detect_encounter_method,
    _extract_locations_from_header,
    _is_floor_pattern,
    _is_metadata_row,
    _looks_like_pokemon_name,
    parse_all_location_csvs,
    parse_gift_static_csv,
    parse_grass_cave_csv,
    parse_locations_csv,
    parse_surfing_fishing_csv,
)


class TestIsMetadataRow:
    """Tests for _is_metadata_row function."""

    @pytest.mark.parametrize(
        "input_cell,expected",
        [
            ("Version: 1.0", True),
            ("version 2.0", True),
            ("Credits:", True),
            ("credits", True),
            ("https://discord.gg/xyz", True),
            ("http://example.com", True),
            ("Discord", True),
            # Empty cells are NOT metadata - row might have data in other columns
            ("", False),
            ("   ", False),
            ("Last Updated: 2024", True),
            ("Made by John", True),
            ("Pokémon Unbound Location Guide", True),
            ("Orange Color: Daytime", True),
            ("Purple Color: Nighttime", True),
            ("Route 1", False),
            ("Pikachu", False),
            ("Ice Hole", False),
            ("Crater Town", False),
        ],
    )
    def test_metadata_detection(self, input_cell: str, expected: bool) -> None:
        """Metadata rows are correctly identified."""
        assert _is_metadata_row(input_cell) == expected


class TestIsFloorPattern:
    """Tests for _is_floor_pattern function."""

    @pytest.mark.parametrize(
        "input_cell,expected",
        [
            ("4F - 1F", True),
            ("2F", True),
            ("B1F", True),
            ("B2F - B1F", True),
            ("1F + 3F", False),  # Not matching exact floor pattern
            ("1F - B1F", True),
            ("Pikachu", False),
            ("Swarm", False),
            ("", False),
        ],
    )
    def test_floor_pattern_detection(self, input_cell: str, expected: bool) -> None:
        """Floor patterns are correctly identified."""
        assert _is_floor_pattern(input_cell) == expected


class TestLooksLikePokemonName:
    """Tests for _looks_like_pokemon_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("Pikachu", True),
            ("Charizard", True),
            ("Mr. Mime", True),
            ("Ho-Oh", True),
            ("Porygon-Z", True),
            ("Nidoran♀", True),
            ("", False),
            ("AB", False),  # Too short
            ("4F", False),  # Starts with number
            ("X", False),  # Skip marker
            ("Fishing", False),  # Method marker
            ("Surfing", False),  # Method marker
            ("Rock Smash", False),  # Method marker
            ("Special Encounter", False),  # Section marker
            ("Easy", False),  # Difficulty
            ("Medium", False),
            ("Hard", False),
            ("Insane", False),
        ],
    )
    def test_pokemon_name_detection(self, input_name: str, expected: bool) -> None:
        """Pokemon names are distinguished from other content."""
        assert _looks_like_pokemon_name(input_name) == expected


class TestDetectEncounterMethod:
    """Tests for _detect_encounter_method function."""

    @pytest.mark.parametrize(
        "location,expected",
        [
            ("Route 1", "grass"),
            ("Route 2", "grass"),
            ("Ice Hole", "grass"),  # Not a "cave" keyword
            ("Icicle Cave", "cave"),
            ("Lost Tunnel", "cave"),
            ("Thundercap Mt.", "cave"),
            ("Frost Mountain", "cave"),
            ("Cinder Volcano", "cave"),
            ("Ruins of Void", "cave"),
            ("Tomb of Borrius", "cave"),
            ("Antisis Sewers", "cave"),
            ("Victory Road", "grass"),
        ],
    )
    def test_encounter_method_detection(self, location: str, expected: str) -> None:
        """Encounter method is correctly detected from location name."""
        assert _detect_encounter_method(location) == expected


class TestExtractLocationsFromHeader:
    """Tests for _extract_locations_from_header function."""

    def test_paired_columns(self) -> None:
        """Location names extracted from even columns only."""
        header = ["Route 1", "", "Route 2", "", "Crater Town", ""]
        locations = _extract_locations_from_header(header)

        assert len(locations) == 3
        assert locations[0] == (0, "Route 1")
        assert locations[1] == (2, "Route 2")
        assert locations[2] == (4, "Crater Town")

    def test_skips_empty_columns(self) -> None:
        """Empty column headers are skipped."""
        header = ["Route 1", "", "", "", "Route 2", ""]
        locations = _extract_locations_from_header(header)

        assert len(locations) == 2
        assert locations[0] == (0, "Route 1")
        assert locations[1] == (4, "Route 2")

    def test_skips_metadata(self) -> None:
        """Metadata in headers is skipped."""
        header = ["Route 1", "", "Version: 1.0", "", "Route 2", ""]
        locations = _extract_locations_from_header(header)

        assert len(locations) == 2
        assert locations[0] == (0, "Route 1")
        assert locations[1] == (4, "Route 2")

    def test_empty_header(self) -> None:
        """Empty header returns empty list."""
        locations = _extract_locations_from_header([])
        assert locations == []


class TestParseGrassCaveCsv:
    """Tests for parse_grass_cave_csv function."""

    def test_simple_csv(self) -> None:
        """Parse simple CSV with one location and Pokemon."""
        csv_content = """Route 1,
Pikachu,
Rattata,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            assert len(df) == 2
            assert df["location_name"].to_list() == ["Route 1", "Route 1"]
            pokemon = set(df["pokemon"].to_list())
            assert "Pikachu" in pokemon
            assert "Rattata" in pokemon
            assert all(m == "grass" for m in df["encounter_method"].to_list())
            assert "requirement" in df.columns
        finally:
            path.unlink()

    def test_multiple_locations(self) -> None:
        """Parse CSV with multiple locations."""
        csv_content = """Route 1,,Route 2,
Pikachu,,Charmander,
Rattata,,Squirtle,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            assert len(df) == 4

            route1_pokemon = df.filter(df["location_name"] == "Route 1")["pokemon"].to_list()
            route2_pokemon = df.filter(df["location_name"] == "Route 2")["pokemon"].to_list()

            assert set(route1_pokemon) == {"Pikachu", "Rattata"}
            assert set(route2_pokemon) == {"Charmander", "Squirtle"}
        finally:
            path.unlink()

    def test_swarm_section(self) -> None:
        """Swarm section marker adds 'Swarm' to encounter notes."""
        csv_content = """Route 1,
Pikachu,
Swarm,
Dunsparce,
Rattata,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            pikachu = df.filter(df["pokemon"] == "Pikachu")
            dunsparce = df.filter(df["pokemon"] == "Dunsparce")
            rattata = df.filter(df["pokemon"] == "Rattata")

            assert pikachu["encounter_notes"].to_list()[0] == ""
            assert "Swarm" in dunsparce["encounter_notes"].to_list()[0]
            assert "Swarm" in rattata["encounter_notes"].to_list()[0]
        finally:
            path.unlink()

    def test_special_encounter_section(self) -> None:
        """Special Encounter marker adds to encounter notes."""
        csv_content = """Route 1,
Pikachu,
Special Encounter,
Snorlax,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            pikachu = df.filter(df["pokemon"] == "Pikachu")
            snorlax = df.filter(df["pokemon"] == "Snorlax")

            assert pikachu["encounter_notes"].to_list()[0] == ""
            assert "Special Encounter" in snorlax["encounter_notes"].to_list()[0]
        finally:
            path.unlink()

    def test_floor_pattern_notes(self) -> None:
        """Floor patterns are added to encounter notes."""
        csv_content = """Ice Hole,
4F - 1F,
Swinub,
2F,
Sneasel,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            swinub = df.filter(df["pokemon"] == "Swinub")
            sneasel = df.filter(df["pokemon"] == "Sneasel")

            assert "4F - 1F" in swinub["encounter_notes"].to_list()[0]
            assert "2F" in sneasel["encounter_notes"].to_list()[0]
        finally:
            path.unlink()

    def test_cave_detection(self) -> None:
        """Cave locations get 'cave' encounter method."""
        csv_content = """Icicle Cave,
Zubat,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            assert df["encounter_method"].to_list()[0] == "cave"
        finally:
            path.unlink()

    def test_pokemon_key_generated(self) -> None:
        """Pokemon keys are slugified correctly."""
        csv_content = """Route 1,
Pikachu,
Nidoran F,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            keys = set(df["pokemon_key"].to_list())
            assert "pikachu" in keys
            assert "nidoran_f" in keys
        finally:
            path.unlink()

    def test_empty_csv(self) -> None:
        """Empty CSV returns empty DataFrame with correct schema."""
        csv_content = ""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_grass_cave_csv(path)
            assert len(df) == 0
            assert "location_name" in df.columns
            assert "pokemon" in df.columns
            assert "pokemon_key" in df.columns
            assert "encounter_method" in df.columns
            assert "encounter_notes" in df.columns
            assert "requirement" in df.columns
        finally:
            path.unlink()


class TestParseSurfingFishingCsv:
    """Tests for parse_surfing_fishing_csv function."""

    def test_surfing_encounters(self) -> None:
        """Parse surfing encounters."""
        csv_content = """Surfing,
,
Route 2,,Route 3,
Tentacool,,Tentacool,
Pelipper,,Pelipper,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)
            assert len(df) == 4
            assert all(m == "surfing" for m in df["encounter_method"].to_list())
        finally:
            path.unlink()

    def test_method_transitions(self) -> None:
        """Methods change when markers are encountered."""
        csv_content = """Surfing,
,
Route 2,
Tentacool,
Old Rod,
Magikarp,
Good Rod,
Staryu,
Super Rod,
Gyarados,
Rock Smash,
Roggenrola,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)

            tentacool = df.filter(df["pokemon"] == "Tentacool")
            magikarp = df.filter(df["pokemon"] == "Magikarp")
            staryu = df.filter(df["pokemon"] == "Staryu")
            gyarados = df.filter(df["pokemon"] == "Gyarados")
            roggenrola = df.filter(df["pokemon"] == "Roggenrola")

            assert tentacool["encounter_method"].to_list()[0] == "surfing"
            assert magikarp["encounter_method"].to_list()[0] == "old_rod"
            assert staryu["encounter_method"].to_list()[0] == "good_rod"
            assert gyarados["encounter_method"].to_list()[0] == "super_rod"
            assert roggenrola["encounter_method"].to_list()[0] == "rock_smash"
        finally:
            path.unlink()

    def test_x_skipped(self) -> None:
        """X markers (no encounters) are skipped."""
        csv_content = """Surfing,
,
Route 7,
X,
Old Rod,
X,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)
            assert len(df) == 0
        finally:
            path.unlink()

    def test_sublocation_notes(self) -> None:
        """Sublocation markers are added to encounter notes."""
        csv_content = """Surfing,
,
Route 13,
Small Island,
Seadra,
West,
Shellder,
Underwater,
Clamperl,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)

            seadra = df.filter(df["pokemon"] == "Seadra")
            shellder = df.filter(df["pokemon"] == "Shellder")
            clamperl = df.filter(df["pokemon"] == "Clamperl")

            assert seadra["encounter_notes"].to_list()[0] == "Small Island"
            assert shellder["encounter_notes"].to_list()[0] == "West"
            assert clamperl["encounter_notes"].to_list()[0] == "Underwater"
        finally:
            path.unlink()

    def test_floor_pattern_in_surfing(self) -> None:
        """Floor patterns work as sublocations in surfing CSV."""
        csv_content = """Surfing,
,
Victory Road,
1F - B1F,
Marill,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)
            marill = df.filter(df["pokemon"] == "Marill")
            assert marill["encounter_notes"].to_list()[0] == "1F - B1F"
        finally:
            path.unlink()

    def test_empty_csv(self) -> None:
        """Empty CSV returns empty DataFrame with correct schema."""
        csv_content = """Surfing,
,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_surfing_fishing_csv(path)
            assert len(df) == 0
            assert "location_name" in df.columns
            assert "encounter_method" in df.columns
            assert "requirement" in df.columns
        finally:
            path.unlink()


class TestParseGiftStaticCsv:
    """Tests for parse_gift_static_csv function."""

    def test_gift_pokemon(self) -> None:
        """Parse gift Pokemon entries."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Gift,,Bellin Town,,,Random,,Return Prof. Log's package
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 1
            assert df["encounter_method"].to_list()[0] == "gift"
            assert df["pokemon"].to_list()[0] == "Random"
            assert "Return Prof. Log's package" in df["requirement"].to_list()[0]
        finally:
            path.unlink()

    def test_static_pokemon(self) -> None:
        """Parse static encounter entries."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Static,,Route 2,,Binacle,,,Daily
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 1
            assert df["encounter_method"].to_list()[0] == "static"
            assert df["pokemon"].to_list()[0] == "Binacle"
            assert df["requirement"].to_list()[0] == "Daily"
            assert df["location_name"].to_list()[0] == "Route 2"
        finally:
            path.unlink()

    def test_mission_reward(self) -> None:
        """Parse mission reward entries."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Mission Reward,,Blizzard City,,Alolan Vulpix Egg,,,Complete the Nine Tails of Snow mission
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 1
            assert df["encounter_method"].to_list()[0] == "mission_reward"
            assert df["location_name"].to_list()[0] == "Blizzard City"
        finally:
            path.unlink()

    def test_random_egg(self) -> None:
        """Parse random egg entries."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Random Egg,,Magnolia Café,,,Kanto Starters,,Free egg one a day
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 1
            assert df["encounter_method"].to_list()[0] == "random_egg"
            assert df["location_name"].to_list()[0] == "Magnolia Café"
        finally:
            path.unlink()

    def test_alternative_pokemon(self) -> None:
        """Parse Pokemon with alternatives (Voltorb/Electrode)."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Static,,Dehara City (Gym),,Voltorb/Electrode,,,None
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            pokemon = set(df["pokemon"].to_list())
            # Should have both alternatives as separate entries
            assert "Voltorb" in pokemon
            assert "Electrode" in pokemon
            assert len(df) == 2
        finally:
            path.unlink()

    def test_continuation_rows(self) -> None:
        """Parse continuation rows that inherit method/location."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Random Egg,,Magnolia Café,,,Kanto Starters,,Free egg one a day
,,,,,Kalos Starters,,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 2
            # Both should have same method and location
            assert all(m == "random_egg" for m in df["encounter_method"].to_list())
            assert all(loc == "Magnolia Café" for loc in df["location_name"].to_list())
        finally:
            path.unlink()

    def test_empty_csv(self) -> None:
        """Empty CSV returns empty DataFrame with correct schema."""
        csv_content = """Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_gift_static_csv(path)
            assert len(df) == 0
            assert "location_name" in df.columns
            assert "encounter_method" in df.columns
            assert "requirement" in df.columns
        finally:
            path.unlink()


class TestParseAllLocationCsvs:
    """Tests for parse_all_location_csvs function."""

    def test_combines_multiple_csv_types(self, tmp_path: Path) -> None:
        """All CSV types are combined into single DataFrame."""
        # Create Grass & Cave CSV
        grass_csv = tmp_path / "Test - Grass & Cave Encounters.csv"
        grass_csv.write_text("""Route 1,
Pikachu,
""")

        # Create Surfing/Fishing CSV
        surfing_csv = tmp_path / "Test - Surfing, Fishing, Rock Smash.csv"
        surfing_csv.write_text("""Surfing,
,
Route 2,
Tentacool,
""")

        # Create Gift/Static CSV
        gift_csv = tmp_path / "Test - Gift & Static Encounters.csv"
        gift_csv.write_text("""Static Encounters + Gift Pokémon,,,,,,,
,,,,,,,
Method,Location,,Possible Pokémon,,,,Requirement
Gift,,Town,,Eevee,,,None
""")

        df = parse_all_location_csvs(tmp_path)

        assert len(df) == 3
        methods = set(df["encounter_method"].to_list())
        assert "grass" in methods
        assert "surfing" in methods
        assert "gift" in methods

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty DataFrame."""
        df = parse_all_location_csvs(tmp_path)
        assert len(df) == 0
        assert "location_name" in df.columns
        assert "encounter_method" in df.columns

    def test_partial_csvs(self, tmp_path: Path) -> None:
        """Works with only some CSV types present."""
        # Only create Grass & Cave CSV
        grass_csv = tmp_path / "Test - Grass & Cave Encounters.csv"
        grass_csv.write_text("""Route 1,
Pikachu,
Rattata,
""")

        df = parse_all_location_csvs(tmp_path)
        assert len(df) == 2
        assert all(m == "grass" for m in df["encounter_method"].to_list())


class TestBackwardCompatibility:
    """Tests for backward compatibility with parse_locations_csv."""

    def test_legacy_function_works(self) -> None:
        """parse_locations_csv still works for Grass & Cave format."""
        csv_content = """Route 1,
Pikachu,
Swarm,
Dunsparce,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_locations_csv(path)
            assert len(df) == 2
            assert "location_name" in df.columns
            assert "pokemon" in df.columns
            assert "pokemon_key" in df.columns
            assert "encounter_method" in df.columns
            assert "encounter_notes" in df.columns
            assert "requirement" in df.columns
        finally:
            path.unlink()
