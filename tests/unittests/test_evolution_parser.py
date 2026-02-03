"""ABOUTME: Tests for evolution parsing from Evolution Table.c.
ABOUTME: Verifies evolution method mapping, reverse detection, and condition building."""

import pytest

from unbounddb.ingestion.evolution_parser import (
    _build_condition,
    _clean_species_name,
    _is_reverse_evolution,
    parse_evolutions,
)


class TestCleanSpeciesName:
    """Tests for _clean_species_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("BULBASAUR", "Bulbasaur"),
            ("CHARIZARD", "Charizard"),
            ("CHARIZARD_MEGA_X", "Charizard Mega X"),
            ("CHARIZARD_MEGA_Y", "Charizard Mega Y"),
            ("VENUSAUR_MEGA", "Venusaur Mega"),
            ("NIDORAN_F", "Nidoran F"),
            ("NIDORAN_M", "Nidoran M"),
            ("MR_MIME", "Mr Mime"),
            ("FARFETCHD", "Farfetchd"),
            ("KYOGRE_PRIMAL", "Kyogre Primal"),
            ("PIKACHU_GIGA", "Pikachu Giga"),
        ],
    )
    def test_species_name_cleaning(self, input_name: str, expected: str) -> None:
        """Species names convert correctly from C constants."""
        assert _clean_species_name(input_name) == expected


class TestIsReverseEvolution:
    """Tests for _is_reverse_evolution function."""

    def test_forward_mega_allowed(self) -> None:
        """Forward mega evolution (base -> mega) is allowed."""
        assert not _is_reverse_evolution(
            "CHARIZARD",
            "CHARIZARD_MEGA_X",
            "EVO_MEGA_EVOLUTION",
            "ITEM_CHARIZARDITE_X",
        )

    def test_reverse_mega_skipped(self) -> None:
        """Reverse mega evolution (mega -> base) is skipped."""
        assert _is_reverse_evolution(
            "CHARIZARD_MEGA_X",
            "CHARIZARD",
            "EVO_MEGA_EVOLUTION",
            "ITEM_NONE",
        )

    def test_forward_primal_allowed(self) -> None:
        """Forward primal reversion is allowed."""
        assert not _is_reverse_evolution(
            "KYOGRE",
            "KYOGRE_PRIMAL",
            "EVO_PRIMAL_REVERSION",
            "ITEM_BLUE_ORB",
        )

    def test_reverse_primal_skipped(self) -> None:
        """Reverse primal reversion is skipped."""
        assert _is_reverse_evolution(
            "KYOGRE_PRIMAL",
            "KYOGRE",
            "EVO_PRIMAL_REVERSION",
            "ITEM_NONE",
        )

    def test_forward_giga_allowed(self) -> None:
        """Forward gigantamax is allowed."""
        assert not _is_reverse_evolution(
            "PIKACHU",
            "PIKACHU_GIGA",
            "EVO_GIGANTAMAX",
            "ITEM_NONE",
        )

    def test_reverse_giga_skipped(self) -> None:
        """Reverse gigantamax is skipped."""
        assert _is_reverse_evolution(
            "PIKACHU_GIGA",
            "PIKACHU",
            "EVO_GIGANTAMAX",
            "ITEM_NONE",
        )

    def test_normal_evolution_allowed(self) -> None:
        """Normal level evolution is allowed."""
        assert not _is_reverse_evolution(
            "BULBASAUR",
            "IVYSAUR",
            "EVO_LEVEL",
            "16",
        )

    def test_mega_with_item_none_skipped(self) -> None:
        """Mega evolution with ITEM_NONE is a reverse and should be skipped."""
        assert _is_reverse_evolution(
            "VENUSAUR",
            "VENUSAUR_MEGA",
            "EVO_MEGA_EVOLUTION",
            "ITEM_NONE",
        )


class TestBuildCondition:
    """Tests for _build_condition function."""

    def test_level_number(self) -> None:
        """Level evolution returns numeric level."""
        assert _build_condition("EVO_LEVEL", "16", "") == "16"
        assert _build_condition("EVO_LEVEL", "36", "") == "36"

    def test_level_day_number(self) -> None:
        """Day level evolution returns numeric level."""
        assert _build_condition("EVO_LEVEL_DAY", "20", "") == "20"

    def test_level_night_number(self) -> None:
        """Night level evolution returns numeric level."""
        assert _build_condition("EVO_LEVEL_NIGHT", "25", "") == "25"

    def test_stone_item(self) -> None:
        """Stone evolution returns item name."""
        assert _build_condition("EVO_ITEM", "ITEM_FIRE_STONE", "") == "Fire Stone"
        assert _build_condition("EVO_ITEM", "ITEM_WATER_STONE", "") == "Water Stone"
        assert _build_condition("EVO_ITEM", "ITEM_THUNDER_STONE", "") == "Thunder Stone"

    def test_mega_stone(self) -> None:
        """Mega evolution returns mega stone name."""
        assert _build_condition("EVO_MEGA_EVOLUTION", "ITEM_CHARIZARDITE_X", "") == "Charizardite X"
        assert _build_condition("EVO_MEGA_EVOLUTION", "ITEM_VENUSAURITE", "") == "Venusaurite"

    def test_trade_empty(self) -> None:
        """Simple trade returns empty condition."""
        assert _build_condition("EVO_TRADE", "0", "") == ""

    def test_trade_with_item(self) -> None:
        """Trade with item returns item name."""
        assert _build_condition("EVO_TRADE_ITEM", "ITEM_METAL_COAT", "") == "Metal Coat"
        assert _build_condition("EVO_TRADE_ITEM", "ITEM_KINGS_ROCK", "") == "Kings Rock"

    def test_friendship_empty(self) -> None:
        """Friendship evolution returns empty condition."""
        assert _build_condition("EVO_FRIENDSHIP", "0", "") == ""
        assert _build_condition("EVO_FRIENDSHIP_DAY", "0", "") == ""
        assert _build_condition("EVO_FRIENDSHIP_NIGHT", "0", "") == ""

    def test_move_name(self) -> None:
        """Move evolution returns move name."""
        assert _build_condition("EVO_MOVE", "MOVE_ROLLOUT", "") == "Rollout"
        assert _build_condition("EVO_MOVE", "MOVE_ANCIENT_POWER", "") == "Ancient Power"

    def test_move_type(self) -> None:
        """Move type evolution returns type name."""
        assert _build_condition("EVO_MOVE_TYPE", "TYPE_FAIRY", "") == "Fairy"
        assert _build_condition("EVO_MOVE_TYPE", "TYPE_DARK", "") == "Dark"

    def test_held_item(self) -> None:
        """Held item evolution returns item name."""
        assert _build_condition("EVO_ITEM_HOLD", "ITEM_RAZOR_FANG", "") == "Razor Fang"
        assert _build_condition("EVO_HOLD_ITEM_DAY", "ITEM_RAZOR_CLAW", "") == "Razor Claw"

    def test_party_pokemon(self) -> None:
        """Party Pokemon evolution returns Pokemon name."""
        assert _build_condition("EVO_OTHER_PARTY_MON", "SPECIES_REMORAID", "") == "Remoraid"

    def test_primal_orb(self) -> None:
        """Primal reversion returns orb name."""
        assert _build_condition("EVO_PRIMAL_REVERSION", "ITEM_BLUE_ORB", "") == "Blue Orb"
        assert _build_condition("EVO_PRIMAL_REVERSION", "ITEM_RED_ORB", "") == "Red Orb"


class TestParseEvolutions:
    """Tests for parse_evolutions function."""

    def test_single_level_evolution(self) -> None:
        """Parse a single level-up evolution."""
        content = """
[SPECIES_BULBASAUR] = {
    {EVO_LEVEL, 16, SPECIES_IVYSAUR, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 1
        assert entries[0].from_pokemon == "Bulbasaur"
        assert entries[0].to_pokemon == "Ivysaur"
        assert entries[0].method == "Level"
        assert entries[0].condition == "16"

    def test_chain_evolution(self) -> None:
        """Parse a two-stage evolution chain."""
        content = """
[SPECIES_BULBASAUR] = {
    {EVO_LEVEL, 16, SPECIES_IVYSAUR, 0},
},
[SPECIES_IVYSAUR] = {
    {EVO_LEVEL, 32, SPECIES_VENUSAUR, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 2

        bulba = next(e for e in entries if e.from_pokemon == "Bulbasaur")
        assert bulba.to_pokemon == "Ivysaur"

        ivy = next(e for e in entries if e.from_pokemon == "Ivysaur")
        assert ivy.to_pokemon == "Venusaur"

    def test_branching_evolution(self) -> None:
        """Parse Eevee with multiple evolution branches."""
        content = """
[SPECIES_EEVEE] = {
    {EVO_FRIENDSHIP_DAY, 0, SPECIES_ESPEON, 0},
    {EVO_FRIENDSHIP_NIGHT, 0, SPECIES_UMBREON, 0},
    {EVO_ITEM, ITEM_FIRE_STONE, SPECIES_FLAREON, 0},
    {EVO_ITEM, ITEM_WATER_STONE, SPECIES_VAPOREON, 0},
    {EVO_ITEM, ITEM_THUNDER_STONE, SPECIES_JOLTEON, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 5

        targets = {e.to_pokemon for e in entries}
        assert "Espeon" in targets
        assert "Umbreon" in targets
        assert "Flareon" in targets
        assert "Vaporeon" in targets
        assert "Jolteon" in targets

    def test_mega_evolution_included(self) -> None:
        """Mega evolutions with items are included."""
        content = """
[SPECIES_CHARIZARD] = {
    {EVO_MEGA_EVOLUTION, ITEM_CHARIZARDITE_X, SPECIES_CHARIZARD_MEGA_X, 0},
    {EVO_MEGA_EVOLUTION, ITEM_CHARIZARDITE_Y, SPECIES_CHARIZARD_MEGA_Y, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 2

        targets = {e.to_pokemon for e in entries}
        assert "Charizard Mega X" in targets
        assert "Charizard Mega Y" in targets

        for entry in entries:
            assert entry.method == "Mega"

    def test_reverse_evolution_skipped(self) -> None:
        """Reverse mega evolutions are filtered out."""
        content = """
[SPECIES_CHARIZARD] = {
    {EVO_MEGA_EVOLUTION, ITEM_CHARIZARDITE_X, SPECIES_CHARIZARD_MEGA_X, 0},
},
[SPECIES_CHARIZARD_MEGA_X] = {
    {EVO_MEGA_EVOLUTION, ITEM_NONE, SPECIES_CHARIZARD, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 1
        assert entries[0].from_pokemon == "Charizard"
        assert entries[0].to_pokemon == "Charizard Mega X"

    def test_evo_none_skipped(self) -> None:
        """EVO_NONE entries are skipped."""
        content = """
[SPECIES_BULBASAUR] = {
    {EVO_LEVEL, 16, SPECIES_IVYSAUR, 0},
    {EVO_NONE, 0, SPECIES_NONE, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 1

    def test_trade_evolution(self) -> None:
        """Trade evolutions are parsed correctly."""
        content = """
[SPECIES_MACHOKE] = {
    {EVO_TRADE, 0, SPECIES_MACHAMP, 0},
},
[SPECIES_ONIX] = {
    {EVO_TRADE_ITEM, ITEM_METAL_COAT, SPECIES_STEELIX, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 2

        machoke = next(e for e in entries if e.from_pokemon == "Machoke")
        assert machoke.method == "Trade"
        assert machoke.condition == ""

        onix = next(e for e in entries if e.from_pokemon == "Onix")
        assert onix.method == "Trade"
        assert onix.condition == "Metal Coat"

    def test_move_evolution(self) -> None:
        """Move-based evolutions are parsed correctly."""
        content = """
[SPECIES_LICKITUNG] = {
    {EVO_MOVE, MOVE_ROLLOUT, SPECIES_LICKILICKY, 0},
},
"""
        entries = parse_evolutions(content)
        assert len(entries) == 1
        assert entries[0].method == "Move"
        assert entries[0].condition == "Rollout"

    def test_empty_content(self) -> None:
        """Empty content returns empty list."""
        entries = parse_evolutions("")
        assert entries == []

    def test_no_valid_evolutions(self) -> None:
        """Content with only EVO_NONE returns empty list."""
        content = """
[SPECIES_PIKACHU] = {
    {EVO_NONE, 0, SPECIES_NONE, 0},
},
"""
        entries = parse_evolutions(content)
        assert entries == []
