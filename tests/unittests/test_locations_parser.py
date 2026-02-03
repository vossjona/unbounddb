"""ABOUTME: Tests for location parsing from wide-format CSV.
ABOUTME: Verifies metadata detection, note detection, and CSV transformation."""

import tempfile
from pathlib import Path

import pytest

from unbounddb.ingestion.locations_parser import (
    _extract_locations_from_header,
    _is_metadata_row,
    _is_note_not_pokemon,
    _looks_like_pokemon_name,
    parse_locations_csv,
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
            ("", True),
            ("   ", True),
            ("Last Updated: 2024", True),
            ("Made by John", True),
            ("Route 1", False),
            ("Pikachu", False),
            ("Ice Hole", False),
            ("Crater Town", False),
        ],
    )
    def test_metadata_detection(self, input_cell: str, expected: bool) -> None:
        """Metadata rows are correctly identified."""
        assert _is_metadata_row(input_cell) == expected


class TestIsNoteNotPokemon:
    """Tests for _is_note_not_pokemon function."""

    @pytest.mark.parametrize(
        "input_cell,expected",
        [
            # Floor patterns
            ("4F - 1F", True),
            ("2F", True),
            ("B1F", True),
            ("B2F - B1F", True),
            # Encounter types
            ("Swarm", True),
            ("swarm", True),
            ("Special Encounter", True),
            ("special encounter", True),
            # Grass types
            ("Yellow Flowers", True),
            ("Purple Flowers", True),
            ("Red Flowers", True),
            ("Tall Grass", True),
            ("Grass", True),
            # Fishing
            ("Surfing", True),
            ("Fishing", True),
            ("Old Rod", True),
            ("Good Rod", True),
            ("Super Rod", True),
            # Other methods
            ("Rock Smash", True),
            ("Headbutt", True),
            ("Honey Tree", True),
            # Time of day
            ("Morning", True),
            ("Day", True),
            ("Night", True),
            # Other encounter types
            ("Horde", True),
            ("Hidden", True),
            ("Ambush", True),
            ("Gift", True),
            ("Trade", True),
            ("Static", True),
            # Empty
            ("", True),
            ("   ", True),
            # Pokemon names (should be False)
            ("Pikachu", False),
            ("Charizard", False),
            ("Mr. Mime", False),
            ("Bulbasaur", False),
        ],
    )
    def test_note_detection(self, input_cell: str, expected: bool) -> None:
        """Notes and encounter types are correctly identified."""
        assert _is_note_not_pokemon(input_cell) == expected


class TestLooksLikePokemonName:
    """Tests for _looks_like_pokemon_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("Pikachu", True),
            ("Charizard", True),
            ("Mr. Mime", True),  # Period is OK for Pokemon names
            ("Bulbasaur", True),
            ("Nidoran♀", True),  # Unicode female symbol OK
            ("Ho-Oh", True),  # Hyphen is OK for Pokemon names
            ("Porygon-Z", True),  # Hyphen is OK for Pokemon names
            ("", False),
            ("AB", False),  # Too short
            ("4F", False),  # Starts with number
            ("2F - 1F", False),  # Note pattern (detected by _is_note_not_pokemon)
            ("https://url", False),  # URL (detected by _is_metadata_row)
        ],
    )
    def test_pokemon_name_detection(self, input_name: str, expected: bool) -> None:
        """Pokemon names are distinguished from other content."""
        assert _looks_like_pokemon_name(input_name) == expected


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


class TestParseLocationsCsv:
    """Tests for parse_locations_csv function."""

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
            df = parse_locations_csv(path)
            assert len(df) == 2
            assert df["location_name"].to_list() == ["Route 1", "Route 1"]
            pokemon = set(df["pokemon"].to_list())
            assert "Pikachu" in pokemon
            assert "Rattata" in pokemon
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
            df = parse_locations_csv(path)
            assert len(df) == 4

            route1_pokemon = df.filter(df["location_name"] == "Route 1")["pokemon"].to_list()
            route2_pokemon = df.filter(df["location_name"] == "Route 2")["pokemon"].to_list()

            assert set(route1_pokemon) == {"Pikachu", "Rattata"}
            assert set(route2_pokemon) == {"Charmander", "Squirtle"}
        finally:
            path.unlink()

    def test_encounter_notes(self) -> None:
        """Encounter notes are captured for Pokemon."""
        csv_content = """Ice Hole,
4F - 1F,
Swinub,
Piloswine,
2F,
Sneasel,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_locations_csv(path)
            assert len(df) == 3

            swinub = df.filter(df["pokemon"] == "Swinub")
            assert swinub["encounter_notes"].to_list()[0] == "4F - 1F"

            sneasel = df.filter(df["pokemon"] == "Sneasel")
            assert sneasel["encounter_notes"].to_list()[0] == "2F"
        finally:
            path.unlink()

    def test_skips_metadata_rows(self) -> None:
        """Metadata rows at bottom are skipped."""
        csv_content = """Route 1,
Pikachu,
Version: 1.0,
Credits: Someone,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_locations_csv(path)
            assert len(df) == 1
            assert df["pokemon"].to_list() == ["Pikachu"]
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
            df = parse_locations_csv(path)
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
            df = parse_locations_csv(path)
            assert len(df) == 0
            assert "location_name" in df.columns
            assert "pokemon" in df.columns
            assert "pokemon_key" in df.columns
            assert "encounter_notes" in df.columns
        finally:
            path.unlink()

    def test_swarm_encounters(self) -> None:
        """Swarm encounters are noted correctly."""
        csv_content = """Route 1,
Swarm,
Dunsparce,
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            path = Path(f.name)

        try:
            df = parse_locations_csv(path)
            assert len(df) == 1
            assert df["pokemon"].to_list() == ["Dunsparce"]
            assert df["encounter_notes"].to_list() == ["Swarm"]
        finally:
            path.unlink()
