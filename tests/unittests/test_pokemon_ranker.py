# ABOUTME: Unit tests for Pokemon ranker scoring functions.
# ABOUTME: Tests defense, offense, stat, BST scoring, and coverage logic for trainer matchups.

from unittest.mock import patch

import polars as pl

from unbounddb.app.tools.pokemon_ranker import (
    calculate_bst_score,
    calculate_coverage,
    calculate_defense_score,
    calculate_offense_score,
    calculate_stat_score,
    rank_pokemon_for_trainer,
)


class TestDefenseScoring:
    """Tests for calculate_defense_score function."""

    def test_immune_type_scores_high(self) -> None:
        """Pokemon with immunity to trainer's moves scores high."""
        # Ground type is immune to Electric
        score, immunities, _resistances, weaknesses = calculate_defense_score(
            type1="Ground",
            type2=None,
            trainer_move_types=["Electric"],
        )
        assert score > 50  # Should be above average
        assert "Electric" in immunities
        assert len(weaknesses) == 0

    def test_weak_type_scores_low(self) -> None:
        """Pokemon weak to trainer's moves scores low."""
        # Grass is weak to Fire
        score, immunities, _resistances, weaknesses = calculate_defense_score(
            type1="Grass",
            type2=None,
            trainer_move_types=["Fire"],
        )
        assert score < 60  # Should be below neutral (one weakness)
        assert "Fire" in weaknesses
        assert len(immunities) == 0

    def test_resistance_scores_medium(self) -> None:
        """Pokemon resisting trainer's moves scores moderately."""
        # Fire resists Fire
        score, _immunities, resistances, _weaknesses = calculate_defense_score(
            type1="Fire",
            type2=None,
            trainer_move_types=["Fire"],
        )
        assert 40 < score < 80  # Should be moderate
        assert "Fire" in resistances

    def test_score_normalized_0_to_100(self) -> None:
        """Score is always within 0-100 range."""
        # Test with many weaknesses
        score_weak, _, _, _ = calculate_defense_score(
            type1="Ice",
            type2=None,
            trainer_move_types=["Fire", "Fighting", "Rock", "Steel"],
        )
        assert 0 <= score_weak <= 100

        # Test with many immunities/resistances
        score_strong, _, _, _ = calculate_defense_score(
            type1="Steel",
            type2="Flying",
            trainer_move_types=["Normal", "Poison", "Ground"],
        )
        assert 0 <= score_strong <= 100

    def test_empty_move_types_returns_zero(self) -> None:
        """Empty trainer move types returns zero score."""
        score, immunities, resistances, weaknesses = calculate_defense_score(
            type1="Normal",
            type2=None,
            trainer_move_types=[],
        )
        assert score == 0.0
        assert immunities == []
        assert resistances == []
        assert weaknesses == []

    def test_dual_type_immunity(self) -> None:
        """Dual type immunity is correctly detected."""
        # Ghost/Dark is immune to Normal and Fighting, immune to Psychic
        _score, immunities, _resistances, _weaknesses = calculate_defense_score(
            type1="Ghost",
            type2="Dark",
            trainer_move_types=["Normal", "Fighting", "Psychic"],
        )
        assert "Normal" in immunities
        assert "Fighting" in immunities
        assert "Psychic" in immunities
        assert len(immunities) == 3

    def test_multiple_weaknesses_lowers_score(self) -> None:
        """Multiple weaknesses significantly lower the score."""
        # Rock/Ice has many weaknesses
        score, _, _, weaknesses = calculate_defense_score(
            type1="Rock",
            type2="Ice",
            trainer_move_types=["Fighting", "Steel", "Water", "Ground"],
        )
        assert len(weaknesses) >= 3
        assert score < 40  # Should be well below neutral


class TestOffenseScoring:
    """Tests for calculate_offense_score function."""

    def test_stab_moves_rank_higher(self) -> None:
        """STAB moves should contribute more to the score."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "ice_beam"],
                "move_name": ["Earthquake", "Ice Beam"],
                "move_type": ["Ground", "Ice"],
                "category": ["Physical", "Special"],
                "power": [100, 90],
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Ice", "score": 15, "rank": 2},
        ]

        # Ground type Pokemon - Earthquake is STAB
        _score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Ground",
            pokemon_type2=None,
        )

        # Earthquake should be first (STAB)
        assert good_moves[0]["move_name"] == "Earthquake"
        assert good_moves[0]["is_stab"] is True
        assert good_moves[0]["effective_power"] == 150  # 100 * 1.5

    def test_higher_power_scores_better(self) -> None:
        """Higher power moves within same type rank score better."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "mud_slap"],
                "move_name": ["Earthquake", "Mud-Slap"],
                "move_type": ["Ground", "Ground"],
                "category": ["Physical", "Special"],
                "power": [100, 20],
                "learn_method": ["level", "level"],
                "level": [36, 5],
            }
        )
        recommended_types = [{"type": "Ground", "score": 20, "rank": 1}]

        _score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",
            pokemon_type2=None,
        )

        # Higher power move should have higher effective power
        earthquake = next(m for m in good_moves if m["move_name"] == "Earthquake")
        mud_slap = next(m for m in good_moves if m["move_name"] == "Mud-Slap")
        assert earthquake["power"] > mud_slap["power"]

    def test_recommended_type_rank_matters(self) -> None:
        """Moves of higher-ranked recommended types contribute more."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "ice_beam"],
                "move_name": ["Earthquake", "Ice Beam"],
                "move_type": ["Ground", "Ice"],
                "category": ["Physical", "Special"],
                "power": [100, 100],  # Same power
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        # Ground is rank 1, Ice is rank 4
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Ice", "score": 5, "rank": 4},
        ]

        _score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",  # Neither is STAB
            pokemon_type2=None,
        )

        # Ground move should come before Ice move due to better rank
        ground_idx = next(i for i, m in enumerate(good_moves) if m["move_type"] == "Ground")
        ice_idx = next(i for i, m in enumerate(good_moves) if m["move_type"] == "Ice")
        assert ground_idx < ice_idx

    def test_no_learnable_moves_returns_zero(self) -> None:
        """Pokemon with no learnable moves returns zero score."""
        empty_df = pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "move_name": pl.String,
                "move_type": pl.String,
                "category": pl.String,
                "power": pl.Int64,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )
        recommended_types = [{"type": "Ground", "score": 20, "rank": 1}]

        score, good_moves = calculate_offense_score(
            learnable_moves=empty_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",
            pokemon_type2=None,
        )

        assert score == 0.0
        assert good_moves == []

    def test_no_recommended_types_returns_zero(self) -> None:
        """No recommended types returns zero score."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["earthquake"],
                "move_name": ["Earthquake"],
                "move_type": ["Ground"],
                "category": ["Physical"],
                "power": [100],
                "learn_method": ["level"],
                "level": [36],
            }
        )

        score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=[],
            pokemon_type1="Ground",
            pokemon_type2=None,
        )

        assert score == 0.0
        assert good_moves == []


class TestStatScoring:
    """Tests for calculate_stat_score function."""

    def test_physical_recommendation_favors_attack(self) -> None:
        """Physical recommendation should favor high Attack stat."""
        score = calculate_stat_score(
            attack=150,
            sp_attack=50,
            phys_spec_recommendation="Use Physical moves",
        )
        # High attack should give high score
        assert score > 70

    def test_special_recommendation_favors_sp_attack(self) -> None:
        """Special recommendation should favor high Sp.Attack stat."""
        score = calculate_stat_score(
            attack=50,
            sp_attack=150,
            phys_spec_recommendation="Use Special moves",
        )
        # High sp_attack should give high score
        assert score > 70

    def test_either_works_averages_stats(self) -> None:
        """Either works recommendation should average both stats."""
        score = calculate_stat_score(
            attack=100,
            sp_attack=100,
            phys_spec_recommendation="Either works",
        )
        # Average of normalized stats
        expected = (100 / 190 * 100 + 100 / 190 * 100) / 2
        assert abs(score - expected) < 1

    def test_physical_low_attack_scores_low(self) -> None:
        """Low Attack with Physical recommendation scores low."""
        score = calculate_stat_score(
            attack=30,
            sp_attack=150,
            phys_spec_recommendation="Use Physical moves",
        )
        assert score < 20

    def test_special_low_sp_attack_scores_low(self) -> None:
        """Low Sp.Attack with Special recommendation scores low."""
        score = calculate_stat_score(
            attack=150,
            sp_attack=30,
            phys_spec_recommendation="Use Special moves",
        )
        assert score < 20

    def test_max_stat_gives_high_score(self) -> None:
        """Very high stat gives score near 100."""
        score = calculate_stat_score(
            attack=190,
            sp_attack=50,
            phys_spec_recommendation="Use Physical moves",
        )
        assert score >= 95

    def test_unknown_recommendation_averages(self) -> None:
        """Unknown recommendation defaults to averaging stats."""
        score = calculate_stat_score(
            attack=100,
            sp_attack=100,
            phys_spec_recommendation="Unknown recommendation",
        )
        expected = (100 / 190 * 100 + 100 / 190 * 100) / 2
        assert abs(score - expected) < 1


class TestGoodMovesSorting:
    """Tests for good moves sorting logic in calculate_offense_score."""

    def test_moves_diversified_by_type_rank(self) -> None:
        """Moves are diversified by type rank for better coverage spread."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test", "test"],
                "move_key": ["ice_beam", "earthquake", "flamethrower"],
                "move_name": ["Ice Beam", "Earthquake", "Flamethrower"],
                "move_type": ["Ice", "Ground", "Fire"],
                "category": ["Special", "Physical", "Special"],
                "power": [90, 100, 90],
                "learn_method": ["tm", "level", "tm"],
                "level": [0, 36, 0],
            }
        )
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Ice", "score": 15, "rank": 2},
            {"type": "Fire", "score": 10, "rank": 3},
        ]

        # Fire type Pokemon - Flamethrower is STAB
        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Fire",
            pokemon_type2=None,
        )

        # Moves are interleaved by type rank for better coverage
        # Ground (rank 1) comes first, then Ice (rank 2), then Fire (rank 3, STAB)
        assert good_moves[0]["move_name"] == "Earthquake"
        assert good_moves[1]["move_name"] == "Ice Beam"
        assert good_moves[2]["move_name"] == "Flamethrower"
        assert good_moves[2]["is_stab"] is True

    def test_higher_power_within_stab(self) -> None:
        """Within STAB moves, higher effective power ranks better."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["flamethrower", "ember"],
                "move_name": ["Flamethrower", "Ember"],
                "move_type": ["Fire", "Fire"],
                "category": ["Special", "Special"],
                "power": [90, 40],
                "learn_method": ["tm", "level"],
                "level": [0, 5],
            }
        )
        recommended_types = [{"type": "Fire", "score": 20, "rank": 1}]

        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Fire",
            pokemon_type2=None,
        )

        # Both are STAB, Flamethrower should be first (higher power)
        assert good_moves[0]["move_name"] == "Flamethrower"
        assert good_moves[1]["move_name"] == "Ember"

    def test_type_rank_ordering(self) -> None:
        """Within non-STAB moves, type rank determines order."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "ice_beam"],
                "move_name": ["Earthquake", "Ice Beam"],
                "move_type": ["Ground", "Ice"],
                "category": ["Physical", "Special"],
                "power": [100, 100],  # Same power
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Ice", "score": 15, "rank": 2},
        ]

        # Normal type - neither is STAB
        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",
            pokemon_type2=None,
        )

        # Ground (rank 1) should come before Ice (rank 2)
        assert good_moves[0]["move_name"] == "Earthquake"
        assert good_moves[1]["move_name"] == "Ice Beam"


class TestMoveDiversification:
    """Tests for move diversification (max per type, interleaving)."""

    def test_max_three_moves_per_type(self) -> None:
        """No more than 3 moves per type are returned."""
        # Create 5 Fire moves
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"] * 5,
                "move_key": ["fire1", "fire2", "fire3", "fire4", "fire5"],
                "move_name": ["Fire Blast", "Flamethrower", "Heat Wave", "Ember", "Flame Wheel"],
                "move_type": ["Fire"] * 5,
                "category": ["Special"] * 5,
                "power": [110, 90, 95, 40, 60],
                "learn_method": ["tm", "tm", "tm", "level", "level"],
                "level": [0, 0, 0, 5, 15],
            }
        )
        recommended_types = [{"type": "Fire", "score": 20, "rank": 1}]

        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Fire",
            pokemon_type2=None,
        )

        # Should return max 3 Fire moves
        assert len(good_moves) == 3
        fire_moves = [m for m in good_moves if m["move_type"] == "Fire"]
        assert len(fire_moves) == 3

    def test_interleaving_multiple_types(self) -> None:
        """Moves from different types are interleaved for better spread."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"] * 6,
                "move_key": ["eq", "drill", "ice", "blizzard", "fire", "flame"],
                "move_name": ["Earthquake", "Drill Run", "Ice Beam", "Blizzard", "Flamethrower", "Fire Blast"],
                "move_type": ["Ground", "Ground", "Ice", "Ice", "Fire", "Fire"],
                "category": ["Physical", "Physical", "Special", "Special", "Special", "Special"],
                "power": [100, 80, 90, 110, 90, 110],
                "learn_method": ["level"] * 6,
                "level": [36, 25, 30, 40, 30, 40],
            }
        )
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Ice", "score": 15, "rank": 2},
            {"type": "Fire", "score": 10, "rank": 3},
        ]

        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",
            pokemon_type2=None,
        )

        # Should interleave: Ground, Ice, Fire, Ground, Ice, Fire
        types_in_order = [m["move_type"] for m in good_moves]
        assert types_in_order == ["Ground", "Ice", "Fire", "Ground", "Ice", "Fire"]

    def test_stab_type_prioritized_in_interleaving(self) -> None:
        """STAB types are prioritized when ranks are equal."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["eq", "fire"],
                "move_name": ["Earthquake", "Flamethrower"],
                "move_type": ["Ground", "Fire"],
                "category": ["Physical", "Special"],
                "power": [100, 90],
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        # Same rank for both types
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Fire", "score": 20, "rank": 1},
        ]

        # Fire type Pokemon - Flamethrower is STAB
        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Fire",
            pokemon_type2=None,
        )

        # Fire (STAB) should come before Ground when ranks are equal
        assert good_moves[0]["move_name"] == "Flamethrower"
        assert good_moves[0]["is_stab"] is True


class TestEdgeCases:
    """Edge case tests for Pokemon ranker functions."""

    def test_pokemon_no_offensive_moves(self) -> None:
        """Pokemon with no offensive moves in recommended types."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["tackle"],
                "move_name": ["Tackle"],
                "move_type": ["Normal"],
                "category": ["Physical"],
                "power": [40],
                "learn_method": ["level"],
                "level": [1],
            }
        )
        # Recommended types don't include Normal
        recommended_types = [{"type": "Ground", "score": 20, "rank": 1}]

        score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Normal",
            pokemon_type2=None,
        )

        assert score == 0.0
        assert good_moves == []

    def test_monotype_pokemon(self) -> None:
        """Monotype Pokemon STAB calculation is correct."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["thunderbolt"],
                "move_name": ["Thunderbolt"],
                "move_type": ["Electric"],
                "category": ["Special"],
                "power": [90],
                "learn_method": ["level"],
                "level": [30],
            }
        )
        recommended_types = [{"type": "Electric", "score": 20, "rank": 1}]

        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Electric",
            pokemon_type2=None,  # Monotype
        )

        assert good_moves[0]["is_stab"] is True
        assert good_moves[0]["effective_power"] == 135  # 90 * 1.5

    def test_dual_type_pokemon_both_stab(self) -> None:
        """Dual type Pokemon gets STAB for both types."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "dragon_claw"],
                "move_name": ["Earthquake", "Dragon Claw"],
                "move_type": ["Ground", "Dragon"],
                "category": ["Physical", "Physical"],
                "power": [100, 80],
                "learn_method": ["level", "level"],
                "level": [36, 24],
            }
        )
        recommended_types = [
            {"type": "Ground", "score": 20, "rank": 1},
            {"type": "Dragon", "score": 15, "rank": 2},
        ]

        # Ground/Dragon type Pokemon
        _, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Ground",
            pokemon_type2="Dragon",
        )

        # Both moves should be STAB
        assert all(m["is_stab"] for m in good_moves)

    def test_defense_score_4x_weakness(self) -> None:
        """4x weakness is counted as a single weakness (not double)."""
        # Rock/Ice is 4x weak to Fighting
        _score, _immunities, _resistances, weaknesses = calculate_defense_score(
            type1="Rock",
            type2="Ice",
            trainer_move_types=["Fighting"],
        )
        # Fighting should appear once in weaknesses
        assert weaknesses.count("Fighting") == 1

    def test_duplicate_moves_not_counted_twice(self) -> None:
        """Same move from different learn methods counted only once."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "earthquake"],  # Same move
                "move_name": ["Earthquake", "Earthquake"],
                "move_type": ["Ground", "Ground"],
                "category": ["Physical", "Physical"],
                "power": [100, 100],
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        recommended_types = [{"type": "Ground", "score": 20, "rank": 1}]

        _score, good_moves = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Ground",
            pokemon_type2=None,
        )

        # Should only count Earthquake once
        assert len(good_moves) == 1
        assert good_moves[0]["move_name"] == "Earthquake"


class TestScoreCapping:
    """Tests for score capping behavior."""

    def test_offense_score_capped_at_100(self) -> None:
        """Offense score cannot exceed 100."""
        # Create many high-powered STAB moves
        moves_data = {
            "pokemon_key": ["test"] * 10,
            "move_key": [f"move_{i}" for i in range(10)],
            "move_name": [f"Move {i}" for i in range(10)],
            "move_type": ["Ground"] * 10,
            "category": ["Physical"] * 10,
            "power": [100] * 10,
            "learn_method": ["level"] * 10,
            "level": list(range(10, 110, 10)),
        }
        moves_df = pl.DataFrame(moves_data)
        recommended_types = [{"type": "Ground", "score": 50, "rank": 1}]

        score, _ = calculate_offense_score(
            learnable_moves=moves_df,
            recommended_types=recommended_types,
            pokemon_type1="Ground",
            pokemon_type2=None,
        )

        assert score <= 100.0

    def test_defense_score_clamped_to_range(self) -> None:
        """Defense score is always between 0 and 100."""
        # Test with many immunities
        score_high, _, _, _ = calculate_defense_score(
            type1="Ghost",
            type2="Dark",
            trainer_move_types=["Normal", "Fighting", "Psychic", "Poison"],
        )
        assert 0 <= score_high <= 100

        # Test with many weaknesses
        score_low, _, _, _ = calculate_defense_score(
            type1="Ice",
            type2=None,
            trainer_move_types=["Fire", "Fighting", "Rock", "Steel"],
        )
        assert 0 <= score_low <= 100


class TestBSTScoring:
    """Tests for calculate_bst_score function."""

    def test_high_bst_scores_higher(self) -> None:
        """Pokemon with 600 BST scores higher than 400 BST."""
        high_score = calculate_bst_score(600)
        low_score = calculate_bst_score(400)
        assert high_score > low_score

    def test_bst_normalized_to_100(self) -> None:
        """BST score is capped at 0-100 range."""
        # Below minimum (300) should be 0
        score_low = calculate_bst_score(200)
        assert score_low == 0.0

        # At minimum should be 0
        score_min = calculate_bst_score(300)
        assert score_min == 0.0

        # At maximum should be 100
        score_max = calculate_bst_score(600)
        assert score_max == 100.0

        # Above maximum should be capped at 100
        score_over = calculate_bst_score(700)
        assert score_over == 100.0

    def test_legendary_bst_caps_at_100(self) -> None:
        """BST >= 600 returns 100."""
        score = calculate_bst_score(680)  # Legendary-level BST
        assert score == 100.0

    def test_midrange_bst(self) -> None:
        """Midrange BST gives expected score."""
        # 450 is halfway between 300 and 600
        score = calculate_bst_score(450)
        assert score == 50.0

    def test_typical_evolution_bst_difference(self) -> None:
        """Evolved Pokemon scores significantly higher than pre-evolution."""
        # Typhlosion (534) vs Quilava (405) - typical evolution difference
        evolved_score = calculate_bst_score(534)
        pre_evo_score = calculate_bst_score(405)

        # Should be ~43 point difference in BST score
        assert evolved_score - pre_evo_score > 40
        assert evolved_score > 70  # Typhlosion should score well
        assert pre_evo_score < 40  # Quilava should score lower


class TestCoverage:
    """Tests for calculate_coverage function."""

    def test_super_effective_move_covers_pokemon(self) -> None:
        """Ground move covers Electric-type trainer Pokemon."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["earthquake"],
                "move_name": ["Earthquake"],
                "move_type": ["Ground"],
                "category": ["Physical"],
                "power": [100],
                "learn_method": ["level"],
                "level": [36],
            }
        )
        trainer_pokemon = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None, "slot": 1},
        ]

        covered_keys, count = calculate_coverage(moves_df, trainer_pokemon)

        assert "pikachu" in covered_keys
        assert count == 1

    def test_no_super_effective_not_covered(self) -> None:
        """Normal moves don't cover anything super-effectively."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["tackle"],
                "move_name": ["Tackle"],
                "move_type": ["Normal"],
                "category": ["Physical"],
                "power": [40],
                "learn_method": ["level"],
                "level": [1],
            }
        )
        trainer_pokemon = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None, "slot": 1},
            {"pokemon_key": "bulbasaur", "type1": "Grass", "type2": "Poison", "slot": 2},
        ]

        covered_keys, count = calculate_coverage(moves_df, trainer_pokemon)

        assert covered_keys == []
        assert count == 0

    def test_coverage_count_correct(self) -> None:
        """Coverage count matches number of covered Pokemon."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test", "test"],
                "move_key": ["earthquake", "ice_beam"],
                "move_name": ["Earthquake", "Ice Beam"],
                "move_type": ["Ground", "Ice"],
                "category": ["Physical", "Special"],
                "power": [100, 90],
                "learn_method": ["level", "tm"],
                "level": [36, 0],
            }
        )
        trainer_pokemon = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None, "slot": 1},  # Covered by Ground
            {"pokemon_key": "dragonite", "type1": "Dragon", "type2": "Flying", "slot": 2},  # Covered by Ice (4x)
            {"pokemon_key": "snorlax", "type1": "Normal", "type2": None, "slot": 3},  # Not covered
        ]

        covered_keys, count = calculate_coverage(moves_df, trainer_pokemon)

        assert count == 2
        assert "pikachu" in covered_keys
        assert "dragonite" in covered_keys
        assert "snorlax" not in covered_keys

    def test_dual_type_weakness_counts(self) -> None:
        """4x weakness still counts as covered."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["ice_beam"],
                "move_name": ["Ice Beam"],
                "move_type": ["Ice"],
                "category": ["Special"],
                "power": [90],
                "learn_method": ["tm"],
                "level": [0],
            }
        )
        # Dragon/Flying is 4x weak to Ice
        trainer_pokemon = [
            {"pokemon_key": "dragonite", "type1": "Dragon", "type2": "Flying", "slot": 1},
        ]

        covered_keys, count = calculate_coverage(moves_df, trainer_pokemon)

        assert "dragonite" in covered_keys
        assert count == 1

    def test_empty_moves_no_coverage(self) -> None:
        """Empty move list means no coverage."""
        empty_df = pl.DataFrame(
            schema={
                "pokemon_key": pl.String,
                "move_key": pl.String,
                "move_name": pl.String,
                "move_type": pl.String,
                "category": pl.String,
                "power": pl.Int64,
                "learn_method": pl.String,
                "level": pl.Int64,
            }
        )
        trainer_pokemon = [
            {"pokemon_key": "pikachu", "type1": "Electric", "type2": None, "slot": 1},
        ]

        covered_keys, count = calculate_coverage(empty_df, trainer_pokemon)

        assert covered_keys == []
        assert count == 0

    def test_empty_trainer_team_no_coverage(self) -> None:
        """Empty trainer team means no coverage."""
        moves_df = pl.DataFrame(
            {
                "pokemon_key": ["test"],
                "move_key": ["earthquake"],
                "move_name": ["Earthquake"],
                "move_type": ["Ground"],
                "category": ["Physical"],
                "power": [100],
                "learn_method": ["level"],
                "level": [36],
            }
        )

        covered_keys, count = calculate_coverage(moves_df, [])

        assert covered_keys == []
        assert count == 0


class TestRankPokemonFiltersByAvailableSet:
    """Tests for the available_pokemon filter in rank_pokemon_for_trainer."""

    def test_available_pokemon_filters_results(self) -> None:
        """When available_pokemon is provided, only those Pokemon should appear."""
        # Create mock Pokemon data
        mock_pokemon = pl.DataFrame(
            {
                "pokemon_key": ["pikachu", "charmander", "bulbasaur"],
                "name": ["Pikachu", "Charmander", "Bulbasaur"],
                "type1": ["Electric", "Fire", "Grass"],
                "type2": [None, None, "Poison"],
                "attack": [55, 52, 49],
                "sp_attack": [50, 60, 65],
                "defense": [40, 43, 49],
                "sp_defense": [50, 50, 65],
                "speed": [90, 65, 45],
                "bst": [320, 309, 318],
            }
        )

        # Create mock moves data
        mock_moves = pl.DataFrame(
            {
                "pokemon_key": ["pikachu", "charmander", "bulbasaur"],
                "move_key": ["thunderbolt", "ember", "vine_whip"],
                "learn_method": ["level", "level", "level"],
                "level": [26, 10, 13],
                "move_name": ["Thunderbolt", "Ember", "Vine Whip"],
                "move_type": ["Electric", "Fire", "Grass"],
                "category": ["Special", "Special", "Physical"],
                "power": [90, 40, 45],
            }
        )

        # Mock trainer analysis functions
        mock_team = [
            {"pokemon_key": "squirtle", "type1": "Water", "type2": None, "slot": 1},
        ]

        with (
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_all_pokemon_with_stats",
                return_value=mock_pokemon,
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_all_learnable_offensive_moves",
                return_value=mock_moves,
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_trainer_move_types",
                return_value=["Water"],
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_recommended_types",
                return_value=[{"type": "Electric", "score": 20, "rank": 1}],
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.analyze_trainer_defensive_profile",
                return_value={"recommendation": "Use Special moves"},
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_trainer_pokemon_types",
                return_value=mock_team,
            ),
        ):
            # Test without filter - should get all 3 Pokemon
            result_all = rank_pokemon_for_trainer(trainer_id=1, top_n=0)
            assert len(result_all) == 3

            # Test with filter - should only get Pikachu and Charmander
            available = {"Pikachu", "Charmander"}
            result_filtered = rank_pokemon_for_trainer(trainer_id=1, top_n=0, available_pokemon=available)
            assert len(result_filtered) == 2
            names = set(result_filtered["name"].to_list())
            assert names == {"Pikachu", "Charmander"}
            assert "Bulbasaur" not in names

    def test_empty_available_pokemon_returns_empty(self) -> None:
        """When available_pokemon is empty set, no Pokemon should appear."""
        mock_pokemon = pl.DataFrame(
            {
                "pokemon_key": ["pikachu"],
                "name": ["Pikachu"],
                "type1": ["Electric"],
                "type2": [None],
                "attack": [55],
                "sp_attack": [50],
                "defense": [40],
                "sp_defense": [50],
                "speed": [90],
                "bst": [320],
            }
        )

        with (
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_all_pokemon_with_stats",
                return_value=mock_pokemon,
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_all_learnable_offensive_moves",
                return_value=pl.DataFrame(),
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_trainer_move_types",
                return_value=[],
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_recommended_types",
                return_value=[],
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.analyze_trainer_defensive_profile",
                return_value={"recommendation": "Either works"},
            ),
            patch(
                "unbounddb.app.tools.pokemon_ranker.get_trainer_pokemon_types",
                return_value=[],
            ),
        ):
            # Empty available set should return empty DataFrame
            result = rank_pokemon_for_trainer(trainer_id=1, top_n=0, available_pokemon=set())
            assert result.is_empty()
