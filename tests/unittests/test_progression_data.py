# ABOUTME: Tests for progression_data.py loading and computation functions.
# ABOUTME: Verifies YAML parsing, dropdown labels, and filter config computation.

from pathlib import Path

import pytest

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.progression.progression_data import (
    ProgressionEntry,
    compute_filter_config,
    get_dropdown_labels,
    load_progression,
)


@pytest.fixture
def sample_entries() -> list[ProgressionEntry]:
    """Small fixture with 5 entries for testing."""
    return [
        ProgressionEntry(
            step=0,
            trainer_name=None,
            trainer_key=None,
            battle_type=None,
            badge_number=0,
            locations=["Route 1"],
            hm_unlocks=[],
            level_cap_vanilla=15,
            level_cap_difficult=20,
            post_game=False,
        ),
        ProgressionEntry(
            step=1,
            trainer_name="Rival Axelrod",
            trainer_key="rival_axelrod",
            battle_type="RIVAL",
            badge_number=None,
            locations=["Route 2"],
            hm_unlocks=[],
            post_game=False,
        ),
        ProgressionEntry(
            step=2,
            trainer_name="Leader Mirskle",
            trainer_key="leader_mirskle",
            battle_type="GYM",
            badge_number=1,
            locations=["Route 3"],
            hm_unlocks=["Surf"],
            level_cap_vanilla=25,
            level_cap_difficult=30,
            post_game=False,
        ),
        ProgressionEntry(
            step=3,
            trainer_name="Rival Axelrod",
            trainer_key="rival_axelrod",
            battle_type="RIVAL",
            badge_number=None,
            locations=["Route 4"],
            hm_unlocks=["Rock Smash"],
            post_game=False,
        ),
        ProgressionEntry(
            step=4,
            trainer_name="Light of Ruin Leader Aklove",
            trainer_key="light_of_ruin_leader_aklove",
            battle_type="LIGHT OF RUIN LEADER",
            badge_number=None,
            locations=["Rift Cave"],
            hm_unlocks=["Dive"],
            post_game=True,
        ),
    ]


class TestLoadProgression:
    """Tests for load_progression function."""

    def test_loads_from_yaml_file(self, tmp_path: Path) -> None:
        """Loads entries from a YAML file with progression and post_game sections."""
        yaml_content = """\
progression:
- trainer: null
  trainer_key: null
  battle_type: null
  badge_number: 0
  locations:
  - Route 1
  hm_unlocks: []
  level_cap_vanilla: 15
  level_cap_difficult: 20
- trainer: Leader Mirskle
  trainer_key: leader_mirskle
  battle_type: GYM
  badge_number: 1
  locations:
  - Route 3
  hm_unlocks:
  - Surf
  level_cap_vanilla: 22
  level_cap_difficult: 26
post_game:
- trainer: Light of Ruin Leader Aklove
  trainer_key: light_of_ruin_leader_aklove
  battle_type: LIGHT OF RUIN LEADER
  badge_number: null
  locations:
  - Rift Cave
  hm_unlocks:
  - Dive
"""
        yaml_file = tmp_path / "test_progression.yml"
        yaml_file.write_text(yaml_content)

        # Clear cache before test
        load_progression.cache_clear()
        entries = load_progression(yaml_file)
        load_progression.cache_clear()

        assert len(entries) == 3
        assert entries[0].step == 0
        assert entries[0].trainer_name is None
        assert entries[0].level_cap_vanilla == 15
        assert entries[1].step == 1
        assert entries[1].trainer_name == "Leader Mirskle"
        assert entries[1].badge_number == 1
        assert entries[2].step == 2
        assert entries[2].post_game is True
        assert entries[2].hm_unlocks == ["Dive"]

    def test_returns_tuple(self, tmp_path: Path) -> None:
        """Returns a tuple (immutable) for caching."""
        yaml_content = (
            "progression:\n- trainer: null\n  trainer_key: null\n"
            "  battle_type: null\n  badge_number: 0\n  locations: []\n  hm_unlocks: []\n"
        )
        yaml_file = tmp_path / "test_progression2.yml"
        yaml_file.write_text(yaml_content)

        load_progression.cache_clear()
        entries = load_progression(yaml_file)
        load_progression.cache_clear()

        assert isinstance(entries, tuple)


class TestGetDropdownLabels:
    """Tests for get_dropdown_labels function."""

    def test_game_start_label(self, sample_entries: list[ProgressionEntry]) -> None:
        """Game start entry has level cap format."""
        labels = get_dropdown_labels(sample_entries)

        assert labels[0] == "Game Start (Lv 15/20)"

    def test_badge_label_includes_badge_number(self, sample_entries: list[ProgressionEntry]) -> None:
        """Gym badge entry shows badge number."""
        labels = get_dropdown_labels(sample_entries)

        assert labels[2] == "Leader Mirskle (Gym - Badge 1)"

    def test_duplicate_trainer_names_get_occurrence_numbers(self, sample_entries: list[ProgressionEntry]) -> None:
        """Duplicate trainer names are distinguished with #N."""
        labels = get_dropdown_labels(sample_entries)

        assert labels[1] == "Rival Axelrod (RIVAL #1)"
        assert labels[3] == "Rival Axelrod (RIVAL #2)"

    def test_post_game_prefix(self, sample_entries: list[ProgressionEntry]) -> None:
        """Post-game entries are prefixed with [Post-Game]."""
        labels = get_dropdown_labels(sample_entries)

        assert labels[4].startswith("[Post-Game]")
        assert "Light of Ruin Leader Aklove" in labels[4]

    def test_label_count_matches_entries(self, sample_entries: list[ProgressionEntry]) -> None:
        """One label per entry."""
        labels = get_dropdown_labels(sample_entries)

        assert len(labels) == len(sample_entries)


class TestComputeFilterConfig:
    """Tests for compute_filter_config function."""

    def test_step_0_only_first_location(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 0 only includes the first entry's locations."""
        config = compute_filter_config(sample_entries, step=0, difficulty=None)

        assert config.accessible_locations == ["Route 1"]
        assert config.has_surf is False
        assert config.has_dive is False
        assert config.has_rock_smash is False
        assert config.post_game is False

    def test_step_0_vanilla_level_cap(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 0 with no difficulty uses vanilla cap."""
        config = compute_filter_config(sample_entries, step=0, difficulty=None)

        assert config.level_cap == 15

    def test_step_0_difficult_level_cap(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 0 with Difficult uses difficult cap."""
        config = compute_filter_config(sample_entries, step=0, difficulty="Difficult")

        assert config.level_cap == 20

    def test_step_2_accumulates_locations_and_hms(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 2 accumulates locations and HMs from entries 0-2."""
        config = compute_filter_config(sample_entries, step=2, difficulty=None)

        assert config.accessible_locations == ["Route 1", "Route 2", "Route 3"]
        assert config.has_surf is True
        assert config.has_dive is False
        assert config.level_cap == 25

    def test_step_2_expert_uses_difficult_cap(self, sample_entries: list[ProgressionEntry]) -> None:
        """Expert difficulty uses difficult level cap."""
        config = compute_filter_config(sample_entries, step=2, difficulty="Expert")

        assert config.level_cap == 30

    def test_step_3_rock_smash_unlocked(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 3 unlocks Rock Smash."""
        config = compute_filter_config(sample_entries, step=3, difficulty=None)

        assert config.has_rock_smash is True
        assert config.has_surf is True  # Still from step 2

    def test_step_4_post_game_and_dive(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step 4 (post-game) sets post_game=True and has_dive=True."""
        config = compute_filter_config(sample_entries, step=4, difficulty=None)

        assert config.post_game is True
        assert config.has_dive is True
        assert "Rift Cave" in (config.accessible_locations or [])

    def test_rod_level_passed_through(self, sample_entries: list[ProgressionEntry]) -> None:
        """Rod level is passed through from parameter."""
        config = compute_filter_config(sample_entries, step=0, difficulty=None, rod_level="Good Rod")

        assert config.rod_level == "Good Rod"

    def test_rod_level_defaults_to_none(self, sample_entries: list[ProgressionEntry]) -> None:
        """Rod level defaults to 'None'."""
        config = compute_filter_config(sample_entries, step=0, difficulty=None)

        assert config.rod_level == "None"

    def test_insane_uses_difficult_cap(self, sample_entries: list[ProgressionEntry]) -> None:
        """Insane difficulty uses difficult level cap."""
        config = compute_filter_config(sample_entries, step=2, difficulty="Insane")

        assert config.level_cap == 30

    def test_any_difficulty_uses_vanilla_cap(self, sample_entries: list[ProgressionEntry]) -> None:
        """'Any' or other strings use vanilla level cap."""
        config = compute_filter_config(sample_entries, step=2, difficulty="Any")

        assert config.level_cap == 25

    def test_returns_location_filter_config(self, sample_entries: list[ProgressionEntry]) -> None:
        """Returns a LocationFilterConfig instance."""
        config = compute_filter_config(sample_entries, step=0, difficulty=None)

        assert isinstance(config, LocationFilterConfig)

    def test_step_beyond_max_clamps(self, sample_entries: list[ProgressionEntry]) -> None:
        """Step beyond max entry count is clamped."""
        config = compute_filter_config(sample_entries, step=999, difficulty=None)

        # Should include all entries
        assert config.post_game is True
        assert config.has_dive is True

    def test_empty_entries_returns_default(self) -> None:
        """Empty entry list returns a default config."""
        config = compute_filter_config([], step=0, difficulty=None)

        assert config.accessible_locations is None
        assert config.level_cap is None
