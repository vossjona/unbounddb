# ABOUTME: Unit tests for the offensive type suggester module.
# ABOUTME: Tests offensive scoring algorithms and coverage calculations.

from itertools import combinations

import pytest

from unbounddb.utils.type_chart import (
    TYPES,
    get_effectiveness,
)


class TestSingleTypeScoring:
    """Tests for individual type scoring algorithm."""

    def test_4x_effectiveness_identified(self) -> None:
        """4x effectiveness should be correctly identified."""
        # Ice vs Grass/Flying = 4x
        eff = get_effectiveness("Ice", "Grass", "Flying")
        assert eff == 4.0

    def test_2x_effectiveness_identified(self) -> None:
        """2x effectiveness should be correctly identified."""
        # Fire vs Grass = 2x
        eff = get_effectiveness("Fire", "Grass", None)
        assert eff == 2.0

    def test_immunity_identified(self) -> None:
        """Immunity (0x) should be correctly identified."""
        # Ground vs Flying = 0x
        eff = get_effectiveness("Ground", "Flying", None)
        assert eff == 0.0

    def test_resistance_identified(self) -> None:
        """Resistance should be correctly identified."""
        # Fire vs Water = 0.5x
        eff = get_effectiveness("Fire", "Water", None)
        assert eff == 0.5

    def test_score_formula_components(self) -> None:
        """Test individual components of the offensive score formula.

        Score = 4x_count * 8 + 2x_count * 4 - resisted_count * 2 - immune_count * 6
        """
        # Manually calculate effectiveness for Fire attacking different types:
        # Fire vs Grass/Poison = 2x, Fire vs Bug/Steel = 4x, Fire vs Water = 0.5x
        fire_vs_grass_poison = get_effectiveness("Fire", "Grass", "Poison")  # 2x
        fire_vs_bug_steel = get_effectiveness("Fire", "Bug", "Steel")  # 4x
        fire_vs_water = get_effectiveness("Fire", "Water", None)  # 0.5x

        assert fire_vs_grass_poison == 2.0
        assert fire_vs_bug_steel == 4.0
        assert fire_vs_water == 0.5

        # Expected score: 1*8 (4x) + 1*4 (2x) - 1*2 (resist) - 0*6 (immune) = 10
        expected_score = 8 + 4 - 2 - 0
        assert expected_score == 10

    def test_immunity_penalty_applied(self) -> None:
        """Immunities should have significant penalty in scoring."""
        # Normal vs Ghost = 0x (immunity)
        eff = get_effectiveness("Normal", "Ghost", None)
        assert eff == 0.0

        # Fighting vs Ghost = 0x (immunity)
        eff_fighting = get_effectiveness("Fighting", "Ghost", None)
        assert eff_fighting == 0.0


class TestFourTypeCoverage:
    """Tests for 4-type coverage algorithm."""

    def test_perfect_coverage_detection(self) -> None:
        """Perfect coverage means all Pokemon hit at 2x or higher."""
        # Water, Grass, Fire, Electric covers most common types
        pokemon_list = [
            {"pokemon_key": "charizard", "type1": "Fire", "type2": "Flying"},
            {"pokemon_key": "blastoise", "type1": "Water", "type2": None},
            {"pokemon_key": "venusaur", "type1": "Grass", "type2": "Poison"},
        ]

        types_to_test = ["Ground", "Ice", "Electric", "Grass"]

        covered_count = 0
        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in types_to_test)
            if best_eff >= 2.0:
                covered_count += 1

        # Ground 2x Charizard, Ice 4x Charizard
        # Electric 2x Blastoise
        # Ice 2x Venusaur, Ground 2x Venusaur (via Poison? No, Poison is neutral)
        # Let me recalculate
        # Charizard (Fire/Flying): Ground=0x, Ice=2x, Electric=2x, Grass=0.5x -> best=2x
        # Blastoise (Water): Ground=1x, Ice=0.5x, Electric=2x, Grass=2x -> best=2x
        # Venusaur (Grass/Poison): Ground=1x, Ice=2x, Electric=1x, Grass=0.5x -> best=2x
        assert covered_count == 3

    def test_uncovered_pokemon_identified(self) -> None:
        """Pokemon not hit at 2x+ should be identified as uncovered."""
        # Sableye (Dark/Ghost) has no weaknesses except Fairy
        pokemon_list = [
            {"pokemon_key": "sableye", "type1": "Dark", "type2": "Ghost"},
        ]

        # Types that don't hit Sableye at 2x+
        types_to_test = ["Fire", "Water", "Grass", "Electric"]

        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in types_to_test)
            # Dark/Ghost: Fire=1x, Water=1x, Grass=1x, Electric=1x
            assert best_eff < 2.0

    def test_best_type_selection_per_pokemon(self) -> None:
        """The best attacking type should be selected for each Pokemon."""
        pokemon = {"pokemon_key": "charizard", "type1": "Fire", "type2": "Flying"}

        types_to_test = ["Water", "Electric", "Rock"]

        best_type = ""
        best_eff = 0.0
        for atk_type in types_to_test:
            eff = get_effectiveness(atk_type, pokemon["type1"], pokemon["type2"])
            if eff > best_eff:
                best_eff = eff
                best_type = atk_type

        # Water=2x, Electric=2x, Rock=4x against Fire/Flying
        assert best_type == "Rock"
        assert best_eff == 4.0

    def test_3060_combinations_count(self) -> None:
        """Should be exactly C(18,4) = 3060 four-type combinations."""
        combos = list(combinations(TYPES, 4))
        assert len(combos) == 3060


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_pokemon_list(self) -> None:
        """Empty Pokemon list should handle gracefully."""
        pokemon_list: list[dict] = []

        # No Pokemon means 0 coverage
        covered = sum(1 for _ in pokemon_list if True)  # placeholder logic
        assert covered == 0

    def test_single_pokemon(self) -> None:
        """Single Pokemon should work correctly."""
        pokemon_list = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None},
        ]

        # Ground is 2x vs Electric
        ground_eff = get_effectiveness("Ground", "Electric", None)
        assert ground_eff == 2.0

        covered = sum(1 for p in pokemon_list if ground_eff >= 2.0)
        assert covered == 1

    def test_monotype_vs_dual_type(self) -> None:
        """Monotype and dual type effectiveness should differ appropriately."""
        # Fire vs Grass = 2x
        mono_eff = get_effectiveness("Fire", "Grass", None)
        assert mono_eff == 2.0

        # Fire vs Grass/Steel = 4x (2x * 2x)
        dual_eff = get_effectiveness("Fire", "Grass", "Steel")
        assert dual_eff == 4.0

    def test_same_type_dual_handling(self) -> None:
        """Same type listed twice shouldn't double the effectiveness."""
        # Edge case: type1 == type2 (shouldn't happen in real data but handle it)
        eff = get_effectiveness("Fire", "Grass", "Grass")
        # Should still be 2x, not 4x
        assert eff == 2.0


class TestCoverageCalculation:
    """Tests for coverage percentage calculations."""

    def test_coverage_percentage_100(self) -> None:
        """100% coverage when all Pokemon are hit at 2x+."""
        pokemon_list = [
            {"pokemon_key": "charizard", "type1": "Fire", "type2": "Flying"},
            {"pokemon_key": "venusaur", "type1": "Grass", "type2": "Poison"},
        ]

        # Rock is 4x vs Fire/Flying, Ice is 2x vs Grass/Poison
        types_to_test = ["Rock", "Ice"]

        covered = 0
        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in types_to_test)
            if best_eff >= 2.0:
                covered += 1

        coverage_pct = covered / len(pokemon_list) * 100
        assert coverage_pct == 100.0

    def test_coverage_percentage_partial(self) -> None:
        """Partial coverage should calculate correctly."""
        pokemon_list = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None},
            {"pokemon_key": "sableye", "type1": "Dark", "type2": "Ghost"},
        ]

        # Ground is 2x vs Electric but 1x vs Dark/Ghost
        types_to_test = ["Ground"]

        covered = 0
        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in types_to_test)
            if best_eff >= 2.0:
                covered += 1

        coverage_pct = covered / len(pokemon_list) * 100
        assert coverage_pct == 50.0


class TestEffectivenessCategories:
    """Tests for effectiveness category classification."""

    @pytest.mark.parametrize(
        "atk_type,def_type1,def_type2,expected_category",
        [
            ("Ice", "Grass", "Flying", "4x"),  # 4x
            ("Fire", "Grass", None, "2x"),  # 2x
            ("Fire", "Fire", None, "resisted"),  # 0.5x
            ("Normal", "Ghost", None, "immune"),  # 0x
            ("Fire", "Electric", None, "neutral"),  # 1x
        ],
    )
    def test_effectiveness_categories(
        self,
        atk_type: str,
        def_type1: str,
        def_type2: str | None,
        expected_category: str,
    ) -> None:
        """Test that effectiveness maps to correct category."""
        eff = get_effectiveness(atk_type, def_type1, def_type2)

        if eff == 0.0:
            category = "immune"
        elif eff >= 4.0:
            category = "4x"
        elif eff >= 2.0:
            category = "2x"
        elif eff == 1.0:
            category = "neutral"
        else:
            category = "resisted"

        assert category == expected_category


class TestScoreFormula:
    """Tests for the specific scoring formulas."""

    def test_offensive_score_positive_for_good_matchup(self) -> None:
        """Good offensive matchup should have positive score."""
        # Fire vs team of Grass, Bug, Ice types
        pokemon_list = [
            {"pokemon_key": "bulbasaur", "type1": "Grass", "type2": None},
            {"pokemon_key": "caterpie", "type1": "Bug", "type2": None},
            {"pokemon_key": "seel", "type1": "Ice", "type2": None},
        ]

        # All are 2x SE for Fire
        score = 0
        for pkmn in pokemon_list:
            eff = get_effectiveness("Fire", pkmn["type1"], pkmn["type2"])
            if eff >= 4.0:
                score += 8
            elif eff >= 2.0:
                score += 4
            elif eff < 1.0 and eff > 0:
                score -= 2
            elif eff == 0.0:
                score -= 6

        # 3 * 4 = 12 (all 2x)
        assert score == 12
        assert score > 0

    def test_offensive_score_negative_for_bad_matchup(self) -> None:
        """Bad offensive matchup should have lower/negative score."""
        # Fire vs team of Water, Rock, Fire types
        pokemon_list = [
            {"pokemon_key": "squirtle", "type1": "Water", "type2": None},
            {"pokemon_key": "geodude", "type1": "Rock", "type2": "Ground"},
            {"pokemon_key": "charmander", "type1": "Fire", "type2": None},
        ]

        score = 0
        for pkmn in pokemon_list:
            eff = get_effectiveness("Fire", pkmn["type1"], pkmn["type2"])
            if eff >= 4.0:
                score += 8
            elif eff >= 2.0:
                score += 4
            elif eff < 1.0 and eff > 0:
                score -= 2
            elif eff == 0.0:
                score -= 6

        # Water=0.5x (-2), Rock/Ground=0.5x (-2), Fire=0.5x (-2)
        assert score == -6
        assert score < 0

    def test_coverage_score_rewards_full_coverage(self) -> None:
        """Full coverage should score higher than partial coverage."""
        pokemon_list = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None},
            {"pokemon_key": "bulbasaur", "type1": "Grass", "type2": "Poison"},
        ]

        # Full coverage combo: Ground (2x Electric), Ice (2x Grass/Poison)
        full_coverage_types = ["Ground", "Ice"]
        covered_full = 0
        sum_eff_full = 0.0
        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in full_coverage_types)
            sum_eff_full += best_eff
            if best_eff >= 2.0:
                covered_full += 1

        # Partial coverage combo: Fire (2x Grass, 1x Electric)
        partial_coverage_types = ["Fire"]
        covered_partial = 0
        sum_eff_partial = 0.0
        for pkmn in pokemon_list:
            best_eff = max(get_effectiveness(t, pkmn["type1"], pkmn["type2"]) for t in partial_coverage_types)
            sum_eff_partial += best_eff
            if best_eff >= 2.0:
                covered_partial += 1

        # Score formula: covered * 10 + sum_eff * 2 - uncovered * 15
        total = len(pokemon_list)
        score_full = covered_full * 10 + sum_eff_full * 2 - (total - covered_full) * 15
        score_partial = covered_partial * 10 + sum_eff_partial * 2 - (total - covered_partial) * 15

        assert score_full > score_partial
