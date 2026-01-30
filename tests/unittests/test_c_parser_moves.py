"""ABOUTME: Tests for move parsing from moves_info.h.
ABOUTME: Verifies MoveInfo extraction and cleaning functions."""

import pytest

from unbounddb.ingestion.c_parser import (
    _clean_category,
    _clean_move_type,
    parse_moves_info,
)


class TestCleanMoveType:
    """Tests for _clean_move_type function."""

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("TYPE_NORMAL", "Normal"),
            ("TYPE_FIRE", "Fire"),
            ("TYPE_WATER", "Water"),
            ("TYPE_ELECTRIC", "Electric"),
            ("TYPE_GRASS", "Grass"),
            ("TYPE_ICE", "Ice"),
            ("TYPE_FIGHTING", "Fighting"),
            ("TYPE_POISON", "Poison"),
            ("TYPE_GROUND", "Ground"),
            ("TYPE_FLYING", "Flying"),
            ("TYPE_PSYCHIC", "Psychic"),
            ("TYPE_BUG", "Bug"),
            ("TYPE_ROCK", "Rock"),
            ("TYPE_GHOST", "Ghost"),
            ("TYPE_DRAGON", "Dragon"),
            ("TYPE_DARK", "Dark"),
            ("TYPE_STEEL", "Steel"),
            ("TYPE_FAIRY", "Fairy"),
        ],
    )
    def test_all_types(self, input_type: str, expected: str) -> None:
        """All 18 types convert correctly."""
        assert _clean_move_type(input_type) == expected


class TestCleanCategory:
    """Tests for _clean_category function."""

    @pytest.mark.parametrize(
        "input_category,expected",
        [
            ("DAMAGE_CATEGORY_PHYSICAL", "Physical"),
            ("DAMAGE_CATEGORY_SPECIAL", "Special"),
            ("DAMAGE_CATEGORY_STATUS", "Status"),
        ],
    )
    def test_categories(self, input_category: str, expected: str) -> None:
        """All categories convert correctly."""
        assert _clean_category(input_category) == expected

    def test_unknown_category_passthrough(self) -> None:
        """Unknown categories pass through unchanged."""
        assert _clean_category("UNKNOWN_CATEGORY") == "UNKNOWN_CATEGORY"


class TestParseMoveInfo:
    """Tests for parse_moves_info function."""

    def test_simple_physical_move(self) -> None:
        """Parse a simple physical move (Scratch)."""
        content = """
[MOVE_SCRATCH] =
{
    .name = COMPOUND_STRING("Scratch"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_NORMAL,
    .accuracy = 100,
    .pp = 35,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.name == "Scratch"
        assert move.type_name == "Normal"
        assert move.category == "Physical"
        assert move.power == 40
        assert move.accuracy == 100
        assert move.pp == 35
        assert move.priority == 0
        assert move.effect == "EFFECT_HIT"
        assert move.makes_contact is True
        assert move.has_secondary_effect is False

    def test_move_with_secondary_effect(self) -> None:
        """Parse a move with secondary effect (Fire Punch)."""
        content = """
[MOVE_FIRE_PUNCH] =
{
    .name = COMPOUND_STRING("Fire Punch"),
    .effect = EFFECT_HIT,
    .power = 75,
    .type = TYPE_FIRE,
    .accuracy = 100,
    .pp = 15,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
    .punchingMove = TRUE,
    .additionalEffects = ADDITIONAL_EFFECTS({
        .moveEffect = MOVE_EFFECT_BURN,
        .chance = 10,
    }),
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.name == "Fire Punch"
        assert move.type_name == "Fire"
        assert move.power == 75
        assert move.makes_contact is True
        assert move.is_punch_move is True
        assert move.has_secondary_effect is True

    def test_status_move(self) -> None:
        """Parse a status move (Swords Dance)."""
        content = """
[MOVE_SWORDS_DANCE] =
{
    .name = COMPOUND_STRING("Swords Dance"),
    .effect = EFFECT_ATTACK_UP_2,
    .power = 0,
    .type = TYPE_NORMAL,
    .accuracy = 0,
    .pp = 20,
    .priority = 0,
    .category = DAMAGE_CATEGORY_STATUS,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.name == "Swords Dance"
        assert move.category == "Status"
        assert move.power == 0
        assert move.accuracy == 0
        assert move.effect == "EFFECT_ATTACK_UP_2"

    def test_negative_priority(self) -> None:
        """Parse a move with negative priority (Trick Room)."""
        content = """
[MOVE_TRICK_ROOM] =
{
    .name = COMPOUND_STRING("Trick Room"),
    .effect = EFFECT_TRICK_ROOM,
    .power = 0,
    .type = TYPE_PSYCHIC,
    .accuracy = 0,
    .pp = 5,
    .priority = -7,
    .category = DAMAGE_CATEGORY_STATUS,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1
        assert moves[0].priority == -7

    def test_multiple_boolean_flags(self) -> None:
        """Parse a move with multiple boolean flags."""
        content = """
[MOVE_BOOMBURST] =
{
    .name = COMPOUND_STRING("Boomburst"),
    .effect = EFFECT_HIT,
    .power = 140,
    .type = TYPE_NORMAL,
    .accuracy = 100,
    .pp = 10,
    .priority = 0,
    .category = DAMAGE_CATEGORY_SPECIAL,
    .soundMove = TRUE,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.is_sound_move is True
        assert move.makes_contact is False
        assert move.is_punch_move is False

    def test_bite_move(self) -> None:
        """Parse a move with bite flag (Crunch)."""
        content = """
[MOVE_CRUNCH] =
{
    .name = COMPOUND_STRING("Crunch"),
    .effect = EFFECT_HIT,
    .power = 80,
    .type = TYPE_DARK,
    .accuracy = 100,
    .pp = 15,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
    .bitingMove = TRUE,
    .additionalEffects = ADDITIONAL_EFFECTS({
        .moveEffect = MOVE_EFFECT_DEF_MINUS_1,
        .chance = 20,
    }),
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.is_bite_move is True
        assert move.has_secondary_effect is True

    def test_pulse_move(self) -> None:
        """Parse a move with pulse flag (Aura Sphere)."""
        content = """
[MOVE_AURA_SPHERE] =
{
    .name = COMPOUND_STRING("Aura Sphere"),
    .effect = EFFECT_HIT,
    .power = 80,
    .type = TYPE_FIGHTING,
    .accuracy = 0,
    .pp = 20,
    .priority = 0,
    .category = DAMAGE_CATEGORY_SPECIAL,
    .pulseMove = TRUE,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1

        move = moves[0]
        assert move.is_pulse_move is True
        assert move.accuracy == 0  # Never misses

    def test_skip_move_none(self) -> None:
        """MOVE_NONE should be skipped."""
        content = """
[MOVE_NONE] =
{
    .name = COMPOUND_STRING("-"),
    .effect = EFFECT_HIT,
    .power = 0,
    .type = TYPE_NORMAL,
    .accuracy = 0,
    .pp = 0,
    .priority = 0,
    .category = DAMAGE_CATEGORY_STATUS,
},
[MOVE_SCRATCH] =
{
    .name = COMPOUND_STRING("Scratch"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_NORMAL,
    .accuracy = 100,
    .pp = 35,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1
        assert moves[0].name == "Scratch"

    def test_gen6_conditional_pp(self) -> None:
        """Parse moves with Gen 6+ conditional PP values."""
        content = """
[MOVE_LEECH_LIFE] =
{
    .name = COMPOUND_STRING("Leech Life"),
    .effect = EFFECT_ABSORB,
    .power = 80,
    .type = TYPE_BUG,
    .accuracy = 100,
    .pp = B_UPDATED_MOVE_DATA >= GEN_6 ? 10 : 15,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1
        # Should extract first number (Gen 6+ value)
        assert moves[0].pp == 10

    def test_gen6_conditional_power(self) -> None:
        """Parse moves with Gen 6+ conditional power values."""
        content = """
[MOVE_THUNDERBOLT] =
{
    .name = COMPOUND_STRING("Thunderbolt"),
    .effect = EFFECT_HIT,
    .power = B_UPDATED_MOVE_DATA >= GEN_6 ? 90 : 95,
    .type = TYPE_ELECTRIC,
    .accuracy = 100,
    .pp = 15,
    .priority = 0,
    .category = DAMAGE_CATEGORY_SPECIAL,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 1
        # Should extract first number (Gen 6+ value)
        assert moves[0].power == 90

    def test_multiple_moves(self) -> None:
        """Parse multiple moves from content."""
        content = """
[MOVE_SCRATCH] =
{
    .name = COMPOUND_STRING("Scratch"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_NORMAL,
    .accuracy = 100,
    .pp = 35,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
},
[MOVE_EMBER] =
{
    .name = COMPOUND_STRING("Ember"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_FIRE,
    .accuracy = 100,
    .pp = 25,
    .priority = 0,
    .category = DAMAGE_CATEGORY_SPECIAL,
},
[MOVE_WATER_GUN] =
{
    .name = COMPOUND_STRING("Water Gun"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_WATER,
    .accuracy = 100,
    .pp = 25,
    .priority = 0,
    .category = DAMAGE_CATEGORY_SPECIAL,
},
"""
        moves = parse_moves_info(content)
        assert len(moves) == 3

        names = [m.name for m in moves]
        assert "Scratch" in names
        assert "Ember" in names
        assert "Water Gun" in names
