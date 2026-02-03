"""ABOUTME: Tests for TM and tutor compatibility file parsing.
ABOUTME: Verifies species extraction and move name parsing from .txt files."""

import pytest

from unbounddb.ingestion.tm_tutor_parser import (
    _clean_species_name,
    _extract_move_name,
    parse_tm_tutor_directory,
    parse_tm_tutor_file,
)


class TestExtractMoveName:
    """Tests for _extract_move_name function."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("24 - Thunderbolt.txt", "Thunderbolt"),
            ("1 - Focus Punch.txt", "Focus Punch"),
            ("100 - Infestation.txt", "Infestation"),
            ("101 - Power-Up Punch.txt", "Power-Up Punch"),
            ("102 - Dazzling Gleam.txt", "Dazzling Gleam"),
            ("10 - Hidden Power.txt", "Hidden Power"),
        ],
    )
    def test_extract_move_name(self, filename: str, expected: str) -> None:
        """Move names extract correctly from filenames."""
        assert _extract_move_name(filename) == expected

    def test_extract_without_number(self) -> None:
        """Filename without number pattern returns full name."""
        assert _extract_move_name("Thunderbolt.txt") == "Thunderbolt"


class TestCleanSpeciesName:
    """Tests for _clean_species_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("PIKACHU", "Pikachu"),
            ("PIKACHU_SURFING", "Pikachu Surfing"),
            ("PIKACHU_FLYING", "Pikachu Flying"),
            ("RAICHU_A", "Raichu A"),
            ("CHARIZARD_MEGA_X", "Charizard Mega X"),
            ("MR_MIME", "Mr Mime"),
            ("NIDORAN_F", "Nidoran F"),
        ],
    )
    def test_species_name_cleaning(self, input_name: str, expected: str) -> None:
        """Species names convert correctly from C constants."""
        assert _clean_species_name(input_name) == expected


class TestParseTmTutorFile:
    """Tests for parse_tm_tutor_file function."""

    def test_parse_single_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse a single TM compatibility file."""
        file_path = tmp_path / "1 - Focus Punch.txt"
        file_path.write_text("""TM01: Focus Punch
CHARMANDER
CHARMELEON
CHARIZARD
""")
        df = parse_tm_tutor_file(file_path, "tm")

        assert len(df) == 3
        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert df["move_key"].unique().to_list() == ["focus_punch"]
        assert df["learn_method"].unique().to_list() == ["tm"]
        assert all(df["level"].is_null())

    def test_parse_tutor_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse a tutor compatibility file."""
        file_path = tmp_path / "1 - Fire Punch.txt"
        file_path.write_text("""Move Tutor: Fire Punch
CHARMANDER
CHARMELEON
""")
        df = parse_tm_tutor_file(file_path, "tutor")

        assert len(df) == 2
        assert df["learn_method"].unique().to_list() == ["tutor"]

    def test_regional_forms(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse file with regional form species."""
        file_path = tmp_path / "24 - Thunderbolt.txt"
        file_path.write_text("""TM24: Thunderbolt
PIKACHU
RAICHU
RAICHU_A
""")
        df = parse_tm_tutor_file(file_path, "tm")

        assert len(df) == 3
        pokemon_keys = df["pokemon_key"].to_list()
        assert "pikachu" in pokemon_keys
        assert "raichu" in pokemon_keys
        assert "raichu_a" in pokemon_keys

    def test_special_forms(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse file with special form species."""
        file_path = tmp_path / "24 - Thunderbolt.txt"
        file_path.write_text("""TM24: Thunderbolt
PIKACHU_SURFING
PIKACHU_FLYING
CHARIZARD_MEGA_X
""")
        df = parse_tm_tutor_file(file_path, "tm")

        assert len(df) == 3
        pokemon_keys = df["pokemon_key"].to_list()
        assert "pikachu_surfing" in pokemon_keys
        assert "pikachu_flying" in pokemon_keys
        assert "charizard_mega_x" in pokemon_keys

    def test_empty_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Empty file returns DataFrame with correct schema."""
        file_path = tmp_path / "1 - Focus Punch.txt"
        file_path.write_text("TM01: Focus Punch\n")

        df = parse_tm_tutor_file(file_path, "tm")

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert len(df) == 0

    def test_blank_lines_ignored(self, tmp_path: pytest.TempPathFactory) -> None:
        """Blank lines in the file are ignored."""
        file_path = tmp_path / "1 - Focus Punch.txt"
        file_path.write_text("""TM01: Focus Punch
PIKACHU

RAICHU

CHARIZARD
""")
        df = parse_tm_tutor_file(file_path, "tm")

        assert len(df) == 3


class TestParseTmTutorDirectory:
    """Tests for parse_tm_tutor_directory function."""

    def test_parse_directory(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse directory with multiple TM files."""
        # Create test files
        (tmp_path / "1 - Focus Punch.txt").write_text("""TM01: Focus Punch
PIKACHU
RAICHU
""")
        (tmp_path / "24 - Thunderbolt.txt").write_text("""TM24: Thunderbolt
PIKACHU
""")
        df = parse_tm_tutor_directory(tmp_path, "tm")

        assert len(df) == 3
        assert df["learn_method"].unique().to_list() == ["tm"]

        # Check both moves are present
        move_keys = df["move_key"].unique().to_list()
        assert "focus_punch" in move_keys
        assert "thunderbolt" in move_keys

    def test_nonexistent_directory(self, tmp_path: pytest.TempPathFactory) -> None:
        """Nonexistent directory returns empty DataFrame with correct schema."""
        nonexistent = tmp_path / "does_not_exist"

        df = parse_tm_tutor_directory(nonexistent, "tm")

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert len(df) == 0

    def test_empty_directory(self, tmp_path: pytest.TempPathFactory) -> None:
        """Empty directory returns empty DataFrame with correct schema."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        df = parse_tm_tutor_directory(empty_dir, "tm")

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert len(df) == 0

    def test_only_txt_files(self, tmp_path: pytest.TempPathFactory) -> None:
        """Only .txt files are parsed, other files ignored."""
        (tmp_path / "1 - Focus Punch.txt").write_text("""TM01: Focus Punch
PIKACHU
""")
        (tmp_path / "README.md").write_text("This is not a TM file")

        df = parse_tm_tutor_directory(tmp_path, "tm")

        assert len(df) == 1
        assert df["move_key"][0] == "focus_punch"

    def test_dataframe_schema(self, tmp_path: pytest.TempPathFactory) -> None:
        """Verify DataFrame has correct schema."""
        (tmp_path / "1 - Focus Punch.txt").write_text("""TM01: Focus Punch
PIKACHU
""")
        df = parse_tm_tutor_directory(tmp_path, "tutor")

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert df["pokemon_key"][0] == "pikachu"
        assert df["move_key"][0] == "focus_punch"
        assert df["learn_method"][0] == "tutor"
        assert df["level"][0] is None
