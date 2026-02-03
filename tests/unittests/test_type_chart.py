# ABOUTME: Unit tests for the Pokemon type effectiveness chart module.
# ABOUTME: Tests type matchups, weaknesses, resistances, immunities, and combinations.

import pytest

from unbounddb.utils.type_chart import (
    EFFECTIVENESS,
    TYPES,
    generate_all_type_combinations,
    get_effectiveness,
    get_immunities,
    get_neutral,
    get_resistances,
    get_weaknesses,
    score_defensive_typing,
)


class TestConstants:
    """Tests for module constants."""

    def test_types_count(self) -> None:
        """There should be exactly 18 types in Gen 6+."""
        assert len(TYPES) == 18

    def test_types_includes_fairy(self) -> None:
        """Fairy type should be included (Gen 6+)."""
        assert "Fairy" in TYPES

    def test_effectiveness_matrix_complete(self) -> None:
        """Every type should have effectiveness against every type."""
        for atk_type in TYPES:
            assert atk_type in EFFECTIVENESS
            for def_type in TYPES:
                assert def_type in EFFECTIVENESS[atk_type]


class TestGetEffectiveness:
    """Tests for get_effectiveness function."""

    # Basic matchups
    def test_super_effective(self) -> None:
        """Water vs Fire = 2x."""
        assert get_effectiveness("Water", "Fire") == 2.0

    def test_not_very_effective(self) -> None:
        """Fire vs Water = 0.5x."""
        assert get_effectiveness("Fire", "Water") == 0.5

    def test_immune(self) -> None:
        """Normal vs Ghost = 0x."""
        assert get_effectiveness("Normal", "Ghost") == 0.0

    def test_neutral(self) -> None:
        """Fire vs Normal = 1x."""
        assert get_effectiveness("Fire", "Normal") == 1.0

    # Dual type matchups
    def test_4x_effective(self) -> None:
        """Rock vs Fire/Flying = 4x."""
        assert get_effectiveness("Rock", "Fire", "Flying") == 4.0

    def test_025x_effective(self) -> None:
        """Fighting vs Poison/Flying = 0.25x."""
        assert get_effectiveness("Fighting", "Poison", "Flying") == 0.25

    def test_dual_type_immunity(self) -> None:
        """Fighting vs Poison/Ghost = 0x (Ghost immunity)."""
        assert get_effectiveness("Fighting", "Poison", "Ghost") == 0.0

    def test_dual_type_cancels_out(self) -> None:
        """Fire vs Grass/Water = 1x (2x * 0.5x)."""
        assert get_effectiveness("Fire", "Grass", "Water") == 1.0

    # CRITICAL: Monotype handling
    def test_monotype_not_doubled(self) -> None:
        """Water vs Fire/Fire = 2x (NOT 4x)."""
        assert get_effectiveness("Water", "Fire", "Fire") == 2.0

    def test_monotype_resistance_not_doubled(self) -> None:
        """Fire vs Fire/Fire = 0.5x (NOT 0.25x)."""
        assert get_effectiveness("Fire", "Fire", "Fire") == 0.5

    def test_monotype_with_none(self) -> None:
        """Water vs Fire/None = 2x."""
        assert get_effectiveness("Water", "Fire", None) == 2.0

    def test_monotype_immunity_not_doubled(self) -> None:
        """Normal vs Ghost/Ghost = 0x."""
        assert get_effectiveness("Normal", "Ghost", "Ghost") == 0.0

    # Additional type interactions (Gen 6+ specific)
    def test_fairy_immune_to_dragon(self) -> None:
        """Dragon vs Fairy = 0x."""
        assert get_effectiveness("Dragon", "Fairy") == 0.0

    def test_fairy_super_effective_on_dragon(self) -> None:
        """Fairy vs Dragon = 2x."""
        assert get_effectiveness("Fairy", "Dragon") == 2.0

    def test_steel_resists_fairy(self) -> None:
        """Fairy vs Steel = 0.5x."""
        assert get_effectiveness("Fairy", "Steel") == 0.5


class TestGetWeaknesses:
    """Tests for get_weaknesses function."""

    def test_fire_weaknesses(self) -> None:
        """Fire is weak to Water, Ground, Rock."""
        weaknesses = get_weaknesses("Fire")
        assert set(weaknesses) == {"Water", "Ground", "Rock"}

    def test_steel_fairy_weaknesses(self) -> None:
        """Steel/Fairy is weak to Fire and Ground only."""
        weaknesses = get_weaknesses("Steel", "Fairy")
        assert set(weaknesses) == {"Fire", "Ground"}

    def test_includes_4x_weakness(self) -> None:
        """Should include 4x weaknesses (Rock vs Fire/Flying)."""
        weaknesses = get_weaknesses("Fire", "Flying")
        assert "Rock" in weaknesses

    def test_electric_monotype(self) -> None:
        """Electric is only weak to Ground."""
        weaknesses = get_weaknesses("Electric")
        assert weaknesses == ["Ground"]


class TestGetResistances:
    """Tests for get_resistances function."""

    def test_steel_resistances(self) -> None:
        """Steel has many resistances."""
        resistances = get_resistances("Steel")
        expected = {
            "Normal",
            "Grass",
            "Ice",
            "Flying",
            "Psychic",
            "Bug",
            "Rock",
            "Dragon",
            "Steel",
            "Fairy",
        }
        assert set(resistances) == expected

    def test_steel_fairy_resistances(self) -> None:
        """Steel/Fairy has extensive resistances including Dragon immunity."""
        resistances = get_resistances("Steel", "Fairy")
        # Dragon is an immunity (0x), not a resistance
        assert "Dragon" not in resistances
        # But should still resist many types
        assert "Bug" in resistances
        assert "Ice" in resistances
        assert "Normal" in resistances

    def test_excludes_immunities(self) -> None:
        """Resistances should not include immunities."""
        resistances = get_resistances("Ghost")
        assert "Normal" not in resistances  # Ghost is immune to Normal
        assert "Fighting" not in resistances  # Ghost is immune to Fighting


class TestGetImmunities:
    """Tests for get_immunities function."""

    def test_ghost_immunities(self) -> None:
        """Ghost is immune to Normal and Fighting."""
        immunities = get_immunities("Ghost")
        assert set(immunities) == {"Normal", "Fighting"}

    def test_flying_ground_immunity(self) -> None:
        """Flying is immune to Ground."""
        immunities = get_immunities("Flying")
        assert immunities == ["Ground"]

    def test_steel_poison_immunity(self) -> None:
        """Steel is immune to Poison."""
        immunities = get_immunities("Steel")
        assert immunities == ["Poison"]

    def test_fairy_dragon_immunity(self) -> None:
        """Fairy is immune to Dragon."""
        immunities = get_immunities("Fairy")
        assert immunities == ["Dragon"]

    def test_dual_type_immunity(self) -> None:
        """Electric/Flying is immune to Ground."""
        immunities = get_immunities("Electric", "Flying")
        assert "Ground" in immunities

    def test_no_immunities(self) -> None:
        """Fire has no immunities."""
        immunities = get_immunities("Fire")
        assert immunities == []


class TestGetNeutral:
    """Tests for get_neutral function."""

    def test_fire_neutral(self) -> None:
        """Fire has neutral matchups against many types."""
        neutral = get_neutral("Fire")
        assert "Normal" in neutral
        assert "Electric" in neutral
        assert "Fighting" in neutral

    def test_neutral_excludes_other_categories(self) -> None:
        """Neutral should not include weaknesses, resistances, or immunities."""
        neutral = get_neutral("Fire")
        assert "Water" not in neutral  # weakness
        assert "Grass" not in neutral  # resistance
        # Fire has no immunities to check


class TestGenerateAllTypeCombinations:
    """Tests for generate_all_type_combinations function."""

    def test_total_count(self) -> None:
        """Should return 171 total combinations (18 + 153)."""
        combinations = generate_all_type_combinations()
        assert len(combinations) == 171

    def test_includes_monotypes(self) -> None:
        """Should include all 18 monotypes."""
        combinations = generate_all_type_combinations()
        monotypes = [c for c in combinations if c[1] is None]
        assert len(monotypes) == 18
        monotype_names = {c[0] for c in monotypes}
        assert monotype_names == set(TYPES)

    def test_no_duplicates(self) -> None:
        """Should have no duplicate combinations."""
        combinations = generate_all_type_combinations()
        # Normalize for comparison (sort tuple elements)
        normalized = set()
        for c in combinations:
            if c[1] is None:
                normalized.add((c[0], None))
            else:
                normalized.add(tuple(sorted([c[0], c[1]])))
        assert len(normalized) == len(combinations)

    def test_normalized_order(self) -> None:
        """Dual types should be in alphabetical order."""
        combinations = generate_all_type_combinations()
        dual_types = [c for c in combinations if c[1] is not None]
        for type1, type2 in dual_types:
            assert type2 is not None  # Type narrowing for mypy
            assert type1 < type2, f"Expected {type1} < {type2}"

    def test_includes_specific_combinations(self) -> None:
        """Should include specific expected combinations."""
        combinations = generate_all_type_combinations()
        assert ("Fire", None) in combinations  # monotype
        assert ("Bug", "Steel") in combinations  # dual type (alphabetical)
        assert ("Steel", "Bug") not in combinations  # should be normalized


class TestScoreDefensiveTyping:
    """Tests for score_defensive_typing function."""

    def test_score_structure(self) -> None:
        """Should return dict with expected keys."""
        score = score_defensive_typing("Fire", None, TYPES)
        expected_keys = {
            "immunities",
            "resistances",
            "neutral",
            "weaknesses",
            "immunity_count",
            "resistance_count",
            "neutral_count",
            "weakness_count",
        }
        assert set(score.keys()) == expected_keys

    def test_counts_match_lists(self) -> None:
        """Counts should match the length of corresponding lists."""
        score = score_defensive_typing("Steel", "Fairy", TYPES)
        assert score["immunity_count"] == len(score["immunities"])
        assert score["resistance_count"] == len(score["resistances"])
        assert score["neutral_count"] == len(score["neutral"])
        assert score["weakness_count"] == len(score["weaknesses"])

    def test_dragon_immune_for_steel_fairy(self) -> None:
        """Steel/Fairy should be immune to Dragon."""
        score = score_defensive_typing("Steel", "Fairy", TYPES)
        assert "Dragon" in score["immunities"]
        assert "Poison" in score["immunities"]

    def test_all_types_categorized(self) -> None:
        """All attacking types should be in exactly one category."""
        score = score_defensive_typing("Water", "Ground", TYPES)
        all_categorized = score["immunities"] + score["resistances"] + score["neutral"] + score["weaknesses"]
        assert len(all_categorized) == len(TYPES)
        assert set(all_categorized) == set(TYPES)

    def test_subset_of_attacking_types(self) -> None:
        """Should work with a subset of attacking types."""
        attacking = ["Fire", "Water", "Grass"]
        score = score_defensive_typing("Fire", None, attacking)
        total = score["immunity_count"] + score["resistance_count"] + score["neutral_count"] + score["weakness_count"]
        assert total == 3

    def test_fire_vs_common_types(self) -> None:
        """Test Fire's defensive profile against common types."""
        attacking = ["Fire", "Water", "Grass", "Electric", "Ground", "Rock"]
        score = score_defensive_typing("Fire", None, attacking)
        assert "Water" in score["weaknesses"]
        assert "Ground" in score["weaknesses"]
        assert "Rock" in score["weaknesses"]
        assert "Fire" in score["resistances"]
        assert "Grass" in score["resistances"]


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.parametrize("pokemon_type", TYPES)
    def test_all_types_have_complete_matchups(self, pokemon_type: str) -> None:
        """Every type should work with all functions."""
        # These should not raise
        get_weaknesses(pokemon_type)
        get_resistances(pokemon_type)
        get_immunities(pokemon_type)
        get_neutral(pokemon_type)

    def test_effectiveness_sum_categories(self) -> None:
        """Sum of all category counts should equal 18 for any defender."""
        weaknesses = get_weaknesses("Normal")
        resistances = get_resistances("Normal")
        immunities = get_immunities("Normal")
        neutral = get_neutral("Normal")
        total = len(weaknesses) + len(resistances) + len(immunities) + len(neutral)
        assert total == 18

    @pytest.mark.parametrize(
        "combo",
        [
            ("Fire", "Fire"),
            ("Water", "Water"),
            ("Ghost", "Ghost"),
            ("Dragon", "Dragon"),
        ],
    )
    def test_monotype_dual_same_as_single(self, combo: tuple[str, str]) -> None:
        """Monotype expressed as dual should equal single type."""
        type1, type2 = combo
        for atk in TYPES:
            single = get_effectiveness(atk, type1, None)
            dual = get_effectiveness(atk, type1, type2)
            assert single == dual, f"{atk} vs {type1}: {single} != {dual}"
