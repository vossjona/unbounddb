"""ABOUTME: Tests for egg move parsing from Egg_Moves.c.
ABOUTME: Verifies egg move extraction and species/move name cleaning."""

import pytest

from unbounddb.ingestion.egg_moves_parser import (
    _clean_move_name,
    _clean_species_name,
    parse_egg_moves,
    parse_egg_moves_file,
)


class TestCleanSpeciesName:
    """Tests for _clean_species_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("BULBASAUR", "Bulbasaur"),
            ("CHARIZARD_MEGA_X", "Charizard Mega X"),
            ("NIDORAN_F", "Nidoran F"),
            ("NIDORAN_M", "Nidoran M"),
            ("MR_MIME", "Mr Mime"),
            ("RAICHU_A", "Raichu A"),
            ("PIKACHU_SURFING", "Pikachu Surfing"),
        ],
    )
    def test_species_name_cleaning(self, input_name: str, expected: str) -> None:
        """Species names convert correctly from C constants."""
        assert _clean_species_name(input_name) == expected


class TestCleanMoveName:
    """Tests for _clean_move_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("SKULLBASH", "Skullbash"),
            ("PETAL_DANCE", "Petal Dance"),
            ("MAGICAL_LEAF", "Magical Leaf"),
            ("THUNDER_WAVE", "Thunder Wave"),
            ("ICE_PUNCH", "Ice Punch"),
        ],
    )
    def test_move_name_cleaning(self, input_name: str, expected: str) -> None:
        """Move names convert correctly from C constants."""
        assert _clean_move_name(input_name) == expected


class TestParseEggMoves:
    """Tests for parse_egg_moves function."""

    def test_single_species_multiple_moves(self) -> None:
        """Parse single species with multiple egg moves."""
        content = """
egg_moves(BULBASAUR,
    MOVE_SKULLBASH,
    MOVE_CHARM,
    MOVE_PETALDANCE),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 3

        pokemon_names = [e.pokemon for e in entries]
        assert all(p == "Bulbasaur" for p in pokemon_names)

        move_names = [e.move for e in entries]
        assert "Skullbash" in move_names
        assert "Charm" in move_names
        assert "Petaldance" in move_names

    def test_multiple_species(self) -> None:
        """Parse multiple species with their egg moves."""
        content = """
egg_moves(BULBASAUR,
    MOVE_CHARM),

egg_moves(CHARMANDER,
    MOVE_BELLYDRUM,
    MOVE_BITE),

egg_moves(SQUIRTLE,
    MOVE_MIRRORCOAT),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 4

        bulbasaur_moves = [e.move for e in entries if e.pokemon == "Bulbasaur"]
        charmander_moves = [e.move for e in entries if e.pokemon == "Charmander"]
        squirtle_moves = [e.move for e in entries if e.pokemon == "Squirtle"]

        assert bulbasaur_moves == ["Charm"]
        assert sorted(charmander_moves) == ["Bellydrum", "Bite"]
        assert squirtle_moves == ["Mirrorcoat"]

    def test_species_with_underscores(self) -> None:
        """Parse species with underscores like NIDORAN_F."""
        content = """
egg_moves(NIDORAN_F,
    MOVE_CHARM,
    MOVE_COUNTER),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 2
        assert entries[0].pokemon == "Nidoran F"
        assert entries[1].pokemon == "Nidoran F"

    def test_regional_forms(self) -> None:
        """Parse regional form species like RAICHU_A."""
        content = """
egg_moves(RAICHU_A,
    MOVE_THUNDER_WAVE),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 1
        assert entries[0].pokemon == "Raichu A"
        assert entries[0].move == "Thunder Wave"

    def test_skip_move_none(self) -> None:
        """MOVE_NONE should be skipped."""
        content = """
egg_moves(PIKACHU,
    MOVE_CHARM,
    MOVE_NONE,
    MOVE_THUNDER_WAVE),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 2
        move_names = [e.move for e in entries]
        assert "Charm" in move_names
        assert "Thunder Wave" in move_names

    def test_skip_species_none(self) -> None:
        """NONE species should be skipped."""
        content = """
egg_moves(NONE,
    MOVE_CHARM),

egg_moves(PIKACHU,
    MOVE_THUNDER_WAVE),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 1
        assert entries[0].pokemon == "Pikachu"

    def test_empty_content(self) -> None:
        """Empty content returns empty list."""
        entries = parse_egg_moves("")
        assert entries == []

    def test_no_egg_moves(self) -> None:
        """Content without egg_moves macros returns empty list."""
        content = """
// Some C comments
#include "stuff.h"
"""
        entries = parse_egg_moves(content)
        assert entries == []

    def test_whitespace_handling(self) -> None:
        """Handle various whitespace in egg_moves macro."""
        content = """
egg_moves(  BULBASAUR  ,
    MOVE_CHARM  ,
    MOVE_TACKLE
),
"""
        entries = parse_egg_moves(content)
        assert len(entries) == 2


class TestParseEggMovesFile:
    """Tests for parse_egg_moves_file function."""

    def test_dataframe_schema(self, tmp_path: pytest.TempPathFactory) -> None:
        """Verify DataFrame has correct schema."""
        file_path = tmp_path / "Egg_Moves.c"
        file_path.write_text("""
egg_moves(BULBASAUR,
    MOVE_CHARM,
    MOVE_TACKLE),
""")
        df = parse_egg_moves_file(file_path)

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert len(df) == 2

    def test_dataframe_values(self, tmp_path: pytest.TempPathFactory) -> None:
        """Verify DataFrame has correct values."""
        file_path = tmp_path / "Egg_Moves.c"
        file_path.write_text("""
egg_moves(BULBASAUR,
    MOVE_CHARM),
""")
        df = parse_egg_moves_file(file_path)

        assert df["pokemon_key"][0] == "bulbasaur"
        assert df["move_key"][0] == "charm"
        assert df["learn_method"][0] == "egg"
        assert df["level"][0] is None

    def test_empty_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Empty file returns DataFrame with correct schema."""
        file_path = tmp_path / "Egg_Moves.c"
        file_path.write_text("")

        df = parse_egg_moves_file(file_path)

        assert df.columns == ["pokemon_key", "move_key", "learn_method", "level"]
        assert len(df) == 0
