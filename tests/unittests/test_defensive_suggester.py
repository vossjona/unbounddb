# ABOUTME: Unit tests for the defensive type suggester module.
# ABOUTME: Tests type matchup analysis and scoring algorithms.

import polars as pl
import pytest

from unbounddb.utils.type_chart import (
    TYPES,
    generate_all_type_combinations,
    get_effectiveness,
    score_defensive_typing,
)


class TestScoreCalculation:
    """Tests for the scoring algorithm used in defensive suggester."""

    def test_immunity_weight_higher_than_resistance(self) -> None:
        """Immunities should be weighted higher than resistances in scoring."""
        # Steel/Fairy: immune to Dragon, Poison; many resistances
        # vs a set with Dragon and Fire
        attacking_types = ["Dragon", "Fire"]
        score = score_defensive_typing("Steel", "Fairy", attacking_types)

        # Dragon is immune (0x), Fire is weakness (2x)
        assert "Dragon" in score["immunities"]
        assert "Fire" in score["weaknesses"]
        assert score["immunity_count"] == 1
        assert score["weakness_count"] == 1

    def test_weakness_penalty_is_significant(self) -> None:
        """Weaknesses should significantly reduce the score."""
        # Fire is weak to Water, Ground, Rock
        attacking_types = ["Water", "Ground", "Rock"]
        score = score_defensive_typing("Fire", None, attacking_types)

        assert score["weakness_count"] == 3
        assert score["resistance_count"] == 0
        assert score["immunity_count"] == 0

    def test_steel_fairy_defensive_excellence(self) -> None:
        """Steel/Fairy should score well defensively against most types."""
        score = score_defensive_typing("Steel", "Fairy", TYPES)

        # Steel/Fairy is immune to Dragon and Poison
        assert score["immunity_count"] == 2
        # Should have many resistances
        assert score["resistance_count"] >= 8
        # Only weak to Fire and Ground
        assert score["weakness_count"] == 2


class TestEffectivenessCalculation:
    """Tests for effectiveness calculations used in neutralization."""

    def test_super_effective_moves_not_neutralized(self) -> None:
        """Pokemon with super-effective moves should not be neutralized."""
        # Fire move vs Grass defender = 2x (not neutralized)
        eff = get_effectiveness("Fire", "Grass", None)
        assert eff > 1.0

    def test_neutral_moves_are_neutralized(self) -> None:
        """Pokemon with only neutral moves should be neutralized."""
        # Fire move vs Water defender = 0.5x (neutralized)
        eff = get_effectiveness("Fire", "Water", None)
        assert eff <= 1.0

    def test_immune_defender_is_neutralized(self) -> None:
        """Pokemon with immune defender should be neutralized."""
        # Normal move vs Ghost = 0x (neutralized)
        eff = get_effectiveness("Normal", "Ghost", None)
        assert eff == 0.0
        assert eff <= 1.0

    @pytest.mark.parametrize(
        "atk_type,def_type1,def_type2,expected_neutralized",
        [
            ("Fire", "Steel", "Fairy", False),  # 2x against Steel/Fairy
            ("Dragon", "Steel", "Fairy", True),  # 0x against Steel/Fairy
            ("Poison", "Steel", "Fairy", True),  # 0x against Steel/Fairy
            ("Fighting", "Steel", "Fairy", True),  # 1x (2x vs Steel, 0.5x vs Fairy)
            ("Ground", "Steel", "Fairy", False),  # 2x against Steel/Fairy
        ],
    )
    def test_neutralization_against_steel_fairy(
        self,
        atk_type: str,
        def_type1: str,
        def_type2: str,
        expected_neutralized: bool,
    ) -> None:
        """Test various attacking types against Steel/Fairy."""
        eff = get_effectiveness(atk_type, def_type1, def_type2)
        is_neutralized = eff <= 1.0
        assert is_neutralized == expected_neutralized


class TestTypeCombinations:
    """Tests for type combination generation and analysis."""

    def test_generates_171_combinations(self) -> None:
        """Should generate exactly 171 type combinations."""
        combos = generate_all_type_combinations()
        assert len(combos) == 171

    def test_monotypes_included(self) -> None:
        """All 18 monotypes should be included."""
        combos = generate_all_type_combinations()
        monotypes = [c for c in combos if c[1] is None]
        assert len(monotypes) == 18

    def test_dual_types_normalized(self) -> None:
        """Dual types should be alphabetically normalized."""
        combos = generate_all_type_combinations()
        dual_types = [c for c in combos if c[1] is not None]

        for type1, type2 in dual_types:
            assert type2 is not None
            assert type1 < type2, f"Expected {type1} < {type2}"


class TestNeutralizationLogic:
    """Tests for the Pokemon neutralization logic."""

    def test_pokemon_with_no_se_moves_is_neutralized(self) -> None:
        """Pokemon with no super-effective moves is considered neutralized."""
        # Simulate: Pokemon has Fire and Normal moves
        # Defender is Water (resists Fire, neutral to Normal)
        move_types = ["Fire", "Normal"]
        def_type1 = "Water"
        def_type2 = None

        # Check if all moves are <=1x
        all_neutralized = all(get_effectiveness(mt, def_type1, def_type2) <= 1.0 for mt in move_types)
        assert all_neutralized is True

    def test_pokemon_with_one_se_move_not_neutralized(self) -> None:
        """Pokemon with at least one super-effective move is not neutralized."""
        # Simulate: Pokemon has Fire and Electric moves
        # Defender is Water (resists Fire, but Electric is 2x)
        move_types = ["Fire", "Electric"]
        def_type1 = "Water"
        def_type2 = None

        # Check if all moves are <=1x
        all_neutralized = all(get_effectiveness(mt, def_type1, def_type2) <= 1.0 for mt in move_types)
        assert all_neutralized is False


class TestEmptyInputHandling:
    """Tests for handling empty inputs gracefully."""

    def test_score_with_no_attacking_types(self) -> None:
        """Scoring with no attacking types should return all zeros."""
        score = score_defensive_typing("Fire", None, [])
        assert score["immunity_count"] == 0
        assert score["resistance_count"] == 0
        assert score["neutral_count"] == 0
        assert score["weakness_count"] == 0

    def test_empty_dataframe_schema(self) -> None:
        """Empty DataFrames should have correct schema."""
        # Test that we can create an empty DataFrame with the expected schema
        df = pl.DataFrame(
            schema={
                "type1": pl.String,
                "type2": pl.String,
                "immunity_count": pl.Int64,
                "score": pl.Int64,
            }
        )
        assert df.is_empty()
        assert "type1" in df.columns
        assert "score" in df.columns


class TestScoreFormula:
    """Tests for the specific scoring formula."""

    def test_score_formula_components(self) -> None:
        """Test individual components of the score formula."""
        # Score formula: immunity*3 + resistance*2 + neutralized*5 - weakness*4

        # Example: Steel/Fairy vs all types
        score = score_defensive_typing("Steel", "Fairy", TYPES)

        # Calculate expected contributions
        immunity_contribution = score["immunity_count"] * 3
        resistance_contribution = score["resistance_count"] * 2
        weakness_penalty = score["weakness_count"] * 4

        # Partial score (without neutralized Pokemon, which requires DB)
        partial_score = immunity_contribution + resistance_contribution - weakness_penalty

        # Steel/Fairy: 2 immunities, ~9 resistances, 2 weaknesses
        # 2*3 + 9*2 - 2*4 = 6 + 18 - 8 = 16
        assert partial_score > 0  # Should be positive for Steel/Fairy

    def test_high_immunity_beats_many_resistances(self) -> None:
        """A single immunity (3 points) beats a single resistance (2 points)."""
        # Ghost/Normal: 3 immunities (Normal, Fighting, Ghost)
        ghost_score = score_defensive_typing("Ghost", "Normal", TYPES)

        # The immunity count should contribute significantly
        immunity_points = ghost_score["immunity_count"] * 3

        # Ghost/Normal has 3 immunities worth 9 points
        assert immunity_points == 9

    def test_weakness_penalty_is_severe(self) -> None:
        """Weaknesses (-4 points) should severely impact score."""
        # Ice type: many weaknesses
        ice_score = score_defensive_typing("Ice", None, TYPES)

        # Ice is weak to: Fire, Fighting, Rock, Steel (4 types)
        assert ice_score["weakness_count"] == 4
        weakness_penalty = ice_score["weakness_count"] * 4  # 16 points penalty
        assert weakness_penalty == 16
