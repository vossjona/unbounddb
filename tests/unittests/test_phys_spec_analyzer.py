# ABOUTME: Unit tests for Physical/Special analyzer functions.
# ABOUTME: Tests classification logic for offensive and defensive profiles.

import pytest

from unbounddb.app.tools.phys_spec_analyzer import (
    classify_pokemon_defensive_profile,
    classify_pokemon_offensive_profile,
)


class TestOffensiveProfileClassification:
    """Tests for classify_pokemon_offensive_profile function."""

    def test_pure_physical_attacker(self) -> None:
        """Pokemon with only Physical moves classified as Physical."""
        moves = [
            {"category": "Physical", "power": 80},
            {"category": "Physical", "power": 60},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Physical"

    def test_pure_special_attacker(self) -> None:
        """Pokemon with only Special moves classified as Special."""
        moves = [
            {"category": "Special", "power": 90},
            {"category": "Special", "power": 70},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Special"

    def test_mixed_attacker(self) -> None:
        """Pokemon with both Physical and Special moves classified as Mixed."""
        moves = [
            {"category": "Physical", "power": 80},
            {"category": "Special", "power": 90},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Mixed"

    def test_status_only_returns_mixed(self) -> None:
        """Pokemon with only Status moves returns Mixed as default."""
        moves = [
            {"category": "Status", "power": 0},
            {"category": "Status", "power": 0},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Mixed"

    def test_zero_power_moves_ignored(self) -> None:
        """Physical/Special moves with power=0 don't count toward classification."""
        moves = [
            {"category": "Physical", "power": 0},  # Should be ignored
            {"category": "Special", "power": 90},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Special"

    def test_physical_with_status_is_physical(self) -> None:
        """Physical moves + Status moves still classified as Physical."""
        moves = [
            {"category": "Physical", "power": 80},
            {"category": "Status", "power": 0},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Physical"

    def test_special_with_status_is_special(self) -> None:
        """Special moves + Status moves still classified as Special."""
        moves = [
            {"category": "Special", "power": 70},
            {"category": "Status", "power": 0},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Special"

    def test_empty_moves_returns_mixed(self) -> None:
        """Empty move list returns Mixed as default."""
        moves: list[dict[str, object]] = []
        assert classify_pokemon_offensive_profile(moves) == "Mixed"

    def test_none_power_treated_as_zero(self) -> None:
        """Moves with None power are treated as zero power."""
        moves = [
            {"category": "Physical", "power": None},
            {"category": "Special", "power": 90},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Special"

    def test_missing_category_ignored(self) -> None:
        """Moves missing category key are ignored."""
        moves = [
            {"power": 80},  # Missing category
            {"category": "Special", "power": 90},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Special"


class TestDefensiveProfileClassification:
    """Tests for classify_pokemon_defensive_profile function."""

    def test_physically_defensive(self) -> None:
        """Defense > Sp.Def * 1.2 classified as Physically Defensive."""
        # 120 > 80 * 1.2 (96) → Physically Defensive
        assert classify_pokemon_defensive_profile(defense=120, sp_defense=80) == "Physically Defensive"

    def test_specially_defensive(self) -> None:
        """Sp.Def > Defense * 1.2 classified as Specially Defensive."""
        # 120 > 80 * 1.2 (96) → Specially Defensive
        assert classify_pokemon_defensive_profile(defense=80, sp_defense=120) == "Specially Defensive"

    def test_balanced_stats(self) -> None:
        """Stats within 20% of each other classified as Balanced."""
        # 100 not > 90 * 1.2 (108) and 90 not > 100 * 1.2 (120)
        assert classify_pokemon_defensive_profile(defense=100, sp_defense=90) == "Balanced"

    def test_exact_threshold_physically_defensive(self) -> None:
        """Test boundary at exactly 20% more Defense."""
        # 121 > 100 * 1.2 (120) → Physically Defensive
        assert classify_pokemon_defensive_profile(defense=121, sp_defense=100) == "Physically Defensive"

    def test_at_threshold_is_balanced(self) -> None:
        """At exactly 120% ratio, should be Balanced (not strictly greater)."""
        # 120 == 100 * 1.2 (120), not > so Balanced
        assert classify_pokemon_defensive_profile(defense=120, sp_defense=100) == "Balanced"

    def test_exact_threshold_specially_defensive(self) -> None:
        """Test boundary at exactly 20% more Sp.Defense."""
        # 121 > 100 * 1.2 (120) → Specially Defensive
        assert classify_pokemon_defensive_profile(defense=100, sp_defense=121) == "Specially Defensive"

    def test_equal_stats_balanced(self) -> None:
        """Equal stats classified as Balanced."""
        assert classify_pokemon_defensive_profile(defense=100, sp_defense=100) == "Balanced"

    def test_low_stats_still_classified(self) -> None:
        """Low stat values are still classified correctly."""
        # 36 > 25 * 1.2 (30) → Physically Defensive
        assert classify_pokemon_defensive_profile(defense=36, sp_defense=25) == "Physically Defensive"

    def test_high_stats_classified(self) -> None:
        """High stat values are still classified correctly."""
        # 200 not > 180 * 1.2 (216) → Balanced
        assert classify_pokemon_defensive_profile(defense=200, sp_defense=180) == "Balanced"


class TestClassificationEdgeCases:
    """Edge case tests for classification functions."""

    def test_offensive_single_physical_move(self) -> None:
        """Single Physical move classifies as Physical."""
        moves = [{"category": "Physical", "power": 100}]
        assert classify_pokemon_offensive_profile(moves) == "Physical"

    def test_offensive_single_special_move(self) -> None:
        """Single Special move classifies as Special."""
        moves = [{"category": "Special", "power": 100}]
        assert classify_pokemon_offensive_profile(moves) == "Special"

    def test_offensive_all_zero_power_returns_mixed(self) -> None:
        """All moves with zero power returns Mixed."""
        moves = [
            {"category": "Physical", "power": 0},
            {"category": "Special", "power": 0},
        ]
        assert classify_pokemon_offensive_profile(moves) == "Mixed"

    def test_defensive_zero_stats(self) -> None:
        """Zero stats handled gracefully (both zero = Balanced)."""
        assert classify_pokemon_defensive_profile(defense=0, sp_defense=0) == "Balanced"

    def test_defensive_one_zero_stat(self) -> None:
        """One zero stat handled correctly."""
        # 50 > 0 * 1.2 (0) → Physically Defensive
        assert classify_pokemon_defensive_profile(defense=50, sp_defense=0) == "Physically Defensive"
        # 50 > 0 * 1.2 (0) → Specially Defensive
        assert classify_pokemon_defensive_profile(defense=0, sp_defense=50) == "Specially Defensive"


class TestMoveDataVariations:
    """Tests for various move data formats."""

    @pytest.mark.parametrize(
        ("moves", "expected"),
        [
            # Standard cases
            ([{"category": "Physical", "power": 80}], "Physical"),
            ([{"category": "Special", "power": 80}], "Special"),
            ([{"category": "Physical", "power": 80}, {"category": "Special", "power": 80}], "Mixed"),
            # Edge cases with missing/None values
            ([{"category": None, "power": 80}], "Mixed"),
            ([{"category": "Physical", "power": None}], "Mixed"),
            ([{}], "Mixed"),
        ],
    )
    def test_various_move_formats(self, moves: list[dict[str, object]], expected: str) -> None:
        """Parametrized test for various move data formats."""
        assert classify_pokemon_offensive_profile(moves) == expected


class TestDefensiveStatVariations:
    """Tests for various defensive stat combinations."""

    @pytest.mark.parametrize(
        ("defense", "sp_defense", "expected"),
        [
            # Clear physically defensive
            (150, 100, "Physically Defensive"),
            (180, 120, "Physically Defensive"),
            # Clear specially defensive
            (100, 150, "Specially Defensive"),
            (120, 180, "Specially Defensive"),
            # Balanced cases
            (100, 100, "Balanced"),
            (110, 100, "Balanced"),
            (100, 110, "Balanced"),
            (115, 100, "Balanced"),
            (100, 115, "Balanced"),
            # Boundary cases
            (120, 100, "Balanced"),  # Exactly 1.2x = not greater
            (100, 120, "Balanced"),  # Exactly 1.2x = not greater
            (121, 100, "Physically Defensive"),  # Just over threshold
            (100, 121, "Specially Defensive"),  # Just over threshold
        ],
    )
    def test_stat_combinations(self, defense: int, sp_defense: int, expected: str) -> None:
        """Parametrized test for various stat combinations."""
        assert classify_pokemon_defensive_profile(defense, sp_defense) == expected
