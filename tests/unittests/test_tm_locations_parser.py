# ABOUTME: Tests for TM locations CSV parser functions.
# ABOUTME: Verifies location extraction, HM detection, alias resolution, and full CSV parsing.

from pathlib import Path

import pytest

from unbounddb.ingestion.tm_locations_parser import (
    _extract_base_location,
    _extract_context_text,
    _extract_required_hms,
    _resolve_location,
    parse_tm_locations_csv,
)


class TestExtractBaseLocation:
    """Tests for _extract_base_location helper."""

    def test_simple_location(self) -> None:
        """Extracts location without parenthetical."""
        assert _extract_base_location("Route 5") == "Route 5"

    def test_location_with_parenthetical(self) -> None:
        """Strips parenthetical from location."""
        result = _extract_base_location("Valley Cave (on B1F after using Rock Climb)")
        assert result == "Valley Cave"

    def test_location_with_brackets(self) -> None:
        """Strips bracketed text from location."""
        result = _extract_base_location("Icy Hole [requires Rock Climb]")
        assert result == "Icy Hole"

    def test_location_with_both_delimiters(self) -> None:
        """Uses first delimiter found."""
        result = _extract_base_location("Icicle Cave (on 3F after beating Trainers[Surf Required])")
        assert result == "Icicle Cave"

    def test_whitespace_stripped(self) -> None:
        """Strips trailing whitespace."""
        result = _extract_base_location("Frost Mountain ( on 2F after)")
        assert result == "Frost Mountain"

    def test_no_delimiters(self) -> None:
        """Returns full string when no delimiters present."""
        assert _extract_base_location("Dehara Dept") == "Dehara Dept"


class TestExtractContextText:
    """Tests for _extract_context_text helper."""

    def test_extracts_parenthetical(self) -> None:
        """Extracts text within parentheses."""
        result = _extract_context_text("Place (after using Surf)")
        assert "after using Surf" in result

    def test_extracts_brackets(self) -> None:
        """Extracts text within brackets."""
        result = _extract_context_text("Place [Surf Required]")
        assert "Surf Required" in result

    def test_extracts_nested(self) -> None:
        """Extracts text from nested delimiters."""
        result = _extract_context_text("Place (inner text [bracket text])")
        assert "inner text" in result
        assert "bracket text" in result

    def test_no_context(self) -> None:
        """Returns empty string when no context."""
        assert _extract_context_text("Dehara Dept") == ""


class TestExtractRequiredHms:
    """Tests for _extract_required_hms helper."""

    def test_surf_detected(self) -> None:
        """Detects Surf requirement."""
        result = _extract_required_hms("Crystal Peak (Large room on 1F after using Surf)")
        assert result == ["Surf"]

    def test_rock_climb_detected(self) -> None:
        """Detects Rock Climb requirement."""
        result = _extract_required_hms("Victory Road (Snowy cliffs after using Rock Climb)")
        assert result == ["Rock Climb"]

    def test_rock_smash_detected(self) -> None:
        """Detects Rock Smash requirement."""
        result = _extract_required_hms("Ruins of Void (on B3F after using Rock Smash)")
        assert result == ["Rock Smash"]

    def test_strength_detected(self) -> None:
        """Detects Strength requirement (including Strengh typo)."""
        result = _extract_required_hms("Icicle Cave (on B1F after pushing a boulder down a hole[Strengh Required])")
        assert result == ["Strength"]

    def test_waterfall_detected(self) -> None:
        """Detects Waterfall requirement."""
        result = _extract_required_hms("Fallshore City (Above the KBT Express Way after using Waterfall)")
        assert result == ["Waterfall"]

    def test_adm_detected_as_dive(self) -> None:
        """Detects ADM as Dive requirement."""
        result = _extract_required_hms("Ruins of Void (on the cliffs after both using the ADM and Rock Climb)")
        assert "Dive" in result
        assert "Rock Climb" in result

    def test_cut_detected(self) -> None:
        """Detects Cut requirement."""
        result = _extract_required_hms("Route 5 (east side of the route after using Cut)")
        assert result == ["Cut"]

    def test_multiple_hms(self) -> None:
        """Detects multiple HM requirements."""
        result = _extract_required_hms(
            "Cinder Volcano (on B1F in the Shadow's storage area after using both Strength & Rock Smash)"
        )
        assert "Rock Smash" in result
        assert "Strength" in result

    def test_no_hms(self) -> None:
        """Returns empty list when no HMs needed."""
        result = _extract_required_hms("Dehara Dept")
        assert result == []

    def test_no_hms_in_location_without_context(self) -> None:
        """No false positives from location-only text."""
        result = _extract_required_hms("Route 14")
        assert result == []

    def test_surf_in_brackets(self) -> None:
        """Detects Surf within bracket context."""
        result = _extract_required_hms("Icicle Cave (on 3F after beating a pair of Ace Trainers[Surf Required])")
        assert result == ["Surf"]

    def test_results_sorted(self) -> None:
        """Results are sorted alphabetically."""
        result = _extract_required_hms("Place (after using Surf and Rock Climb)")
        assert result == sorted(result)

    def test_rock_climb_in_brackets_different_location(self) -> None:
        """Detects Rock Climb even when in a bracketed sub-reference."""
        result = _extract_required_hms("Icy Hole (Help Clown escape; requires Rock Climb[Bellin Town])")
        assert result == ["Rock Climb"]

    def test_surf_and_cut_combined(self) -> None:
        """Detects both Surf and Cut."""
        result = _extract_required_hms("Auburn Waterway (in the surf area after using both surf and cut)")
        assert "Cut" in result
        assert "Surf" in result


class TestResolveLocation:
    """Tests for _resolve_location helper."""

    def test_known_alias(self) -> None:
        """Resolves known alias."""
        assert _resolve_location("Dehara Dept") == "Dehara City"

    def test_thundercap_mountain(self) -> None:
        """Resolves Thundercap Mountain to Epidimy Town."""
        assert _resolve_location("Thundercap Mountain") == "Epidimy Town"

    def test_thundercap_mt(self) -> None:
        """Resolves abbreviated Thundercap Mt."""
        assert _resolve_location("Thundercap Mt") == "Epidimy Town"

    def test_unknown_location_unchanged(self) -> None:
        """Unknown locations pass through unchanged."""
        assert _resolve_location("Route 5") == "Route 5"

    def test_forst_mountain_typo(self) -> None:
        """Resolves Forst Mountain typo."""
        assert _resolve_location("Forst Mountain") == "Frost Mountain"


class TestParseTmLocationsCsv:
    """Tests for parse_tm_locations_csv main function."""

    @pytest.fixture
    def sample_csv(self, tmp_path: Path) -> Path:
        """Create a small sample CSV for testing."""
        csv_content = (
            "ID,NAME,TYPE,PLACE\n"
            '003,Water Pulse,water,"Valley Cave (on B1F after using Rock Climb)"\n'
            "015,Hyper Beam,normal,Dehara Dept\n"
            '082,Sleep Talk,normal,"Battle Tower (purchased for 32 BP)"\n'
            '076,Stealth Rock,rock,"Cinder Volcano (on B1F after using both Strength & Rock Smash)"\n'
        )
        csv_path = tmp_path / "tm_locations.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_returns_dataframe(self, sample_csv: Path) -> None:
        """Returns a Polars DataFrame."""
        df = parse_tm_locations_csv(sample_csv)
        assert len(df) == 4

    def test_tm_number_column(self, sample_csv: Path) -> None:
        """Has correct tm_number values."""
        df = parse_tm_locations_csv(sample_csv)
        assert df["tm_number"].to_list() == [3, 15, 82, 76]

    def test_move_key_slugified(self, sample_csv: Path) -> None:
        """Move names are slugified correctly."""
        df = parse_tm_locations_csv(sample_csv)
        assert "water_pulse" in df["move_key"].to_list()
        assert "hyper_beam" in df["move_key"].to_list()

    def test_location_resolved(self, sample_csv: Path) -> None:
        """Locations are resolved via aliases."""
        df = parse_tm_locations_csv(sample_csv)
        locations = df["location"].to_list()
        assert "Valley Cave" in locations
        assert "Dehara City" in locations  # Dehara Dept -> Dehara City

    def test_required_hms_extracted(self, sample_csv: Path) -> None:
        """Required HMs are extracted from place text."""
        df = parse_tm_locations_csv(sample_csv)
        water_pulse = df.filter(df["tm_number"] == 3)
        assert water_pulse["required_hms"][0] == "Rock Climb"

    def test_multiple_hms(self, sample_csv: Path) -> None:
        """Multiple HMs are comma-separated."""
        df = parse_tm_locations_csv(sample_csv)
        stealth_rock = df.filter(df["tm_number"] == 76)
        hms = stealth_rock["required_hms"][0]
        assert "Rock Smash" in hms
        assert "Strength" in hms

    def test_no_hms_is_empty_string(self, sample_csv: Path) -> None:
        """TMs with no HM requirements have empty string."""
        df = parse_tm_locations_csv(sample_csv)
        hyper_beam = df.filter(df["tm_number"] == 15)
        assert hyper_beam["required_hms"][0] == ""

    def test_post_game_flag(self, sample_csv: Path) -> None:
        """Battle Tower TMs are flagged as post-game."""
        df = parse_tm_locations_csv(sample_csv)
        sleep_talk = df.filter(df["tm_number"] == 82)
        assert sleep_talk["is_post_game"][0] is True

    def test_non_post_game_flag(self, sample_csv: Path) -> None:
        """Non-Battle Tower TMs are not flagged as post-game."""
        df = parse_tm_locations_csv(sample_csv)
        water_pulse = df.filter(df["tm_number"] == 3)
        assert water_pulse["is_post_game"][0] is False

    def test_place_raw_preserved(self, sample_csv: Path) -> None:
        """Original PLACE text is preserved for debugging."""
        df = parse_tm_locations_csv(sample_csv)
        water_pulse = df.filter(df["tm_number"] == 3)
        assert "Rock Climb" in water_pulse["place_raw"][0]
