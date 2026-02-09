# ABOUTME: Tests for TM availability filtering based on game progression.
# ABOUTME: Verifies get_available_tm_move_keys with various filter configs.

from pathlib import Path

import duckdb
import polars as pl
import pytest

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.app.tm_availability import get_available_tm_move_keys


@pytest.fixture
def db_with_tm_locations(tmp_path: Path) -> Path:
    """Create a temp DuckDB with a tm_locations table."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))

    df = pl.DataFrame(  # noqa: F841 - used by DuckDB SQL below
        {
            "tm_number": [1, 2, 3, 4, 5],
            "move_name": ["Focus Punch", "Dragon Claw", "Water Pulse", "Calm Mind", "Sleep Talk"],
            "move_key": ["focus_punch", "dragon_claw", "water_pulse", "calm_mind", "sleep_talk"],
            "location": ["Victory Road", "Victory Road", "Valley Cave", "Fallshore City", "Battle Tower"],
            "required_hms": ["", "Rock Climb", "Rock Climb", "", ""],
            "place_raw": [
                "Victory Road (Outdoor hedge maze)",
                "Victory Road (Snowy cliffs after using Rock Climb)",
                "Valley Cave (on B1F after using Rock Climb)",
                "Fallshore City (Purchase in the marketplace)",
                "Battle Tower (purchased for 32 BP)",
            ],
            "is_post_game": [False, False, False, False, True],
        }
    )

    conn.execute("CREATE TABLE tm_locations AS SELECT * FROM df")
    conn.close()
    return db_path


class TestGetAvailableTmMoveKeys:
    """Tests for get_available_tm_move_keys function."""

    def test_none_config_returns_none(self, db_with_tm_locations: Path) -> None:
        """No filter config means no filtering."""
        result = get_available_tm_move_keys(None, db_path=db_with_tm_locations)
        assert result is None

    def test_missing_table_returns_none(self, tmp_path: Path) -> None:
        """Missing tm_locations table returns None (graceful fallback)."""
        db_path = tmp_path / "empty.duckdb"
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE pokemon (name VARCHAR)")
        conn.close()

        config = LocationFilterConfig(accessible_locations=["Route 1"])
        result = get_available_tm_move_keys(config, db_path=db_path)
        assert result is None

    def test_all_locations_accessible(self, db_with_tm_locations: Path) -> None:
        """All TMs available when all locations accessible and post-game."""
        config = LocationFilterConfig(
            accessible_locations=["Victory Road", "Valley Cave", "Fallshore City", "Battle Tower"],
            available_hms=frozenset({"Rock Climb", "Surf"}),
            post_game=True,
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert len(result) == 5

    def test_location_filtering(self, db_with_tm_locations: Path) -> None:
        """Only TMs in accessible locations are available."""
        config = LocationFilterConfig(
            accessible_locations=["Fallshore City"],
            available_hms=frozenset(),
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert result == {"calm_mind"}

    def test_hm_filtering(self, db_with_tm_locations: Path) -> None:
        """TMs behind HMs are excluded when HMs unavailable."""
        config = LocationFilterConfig(
            accessible_locations=["Victory Road", "Valley Cave", "Fallshore City"],
            available_hms=frozenset(),  # No HMs
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        # focus_punch (no HMs) + calm_mind (no HMs) = 2
        assert "focus_punch" in result
        assert "calm_mind" in result
        assert "dragon_claw" not in result  # Needs Rock Climb
        assert "water_pulse" not in result  # Needs Rock Climb

    def test_hm_unlocked(self, db_with_tm_locations: Path) -> None:
        """TMs behind HMs are included when HMs available."""
        config = LocationFilterConfig(
            accessible_locations=["Victory Road", "Valley Cave", "Fallshore City"],
            available_hms=frozenset({"Rock Climb"}),
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert "dragon_claw" in result
        assert "water_pulse" in result

    def test_post_game_excluded(self, db_with_tm_locations: Path) -> None:
        """Post-game TMs excluded when not in post-game."""
        config = LocationFilterConfig(
            accessible_locations=["Victory Road", "Valley Cave", "Fallshore City", "Battle Tower"],
            available_hms=frozenset({"Rock Climb"}),
            post_game=False,
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert "sleep_talk" not in result

    def test_post_game_included(self, db_with_tm_locations: Path) -> None:
        """Post-game TMs included when in post-game."""
        config = LocationFilterConfig(
            accessible_locations=["Battle Tower"],
            available_hms=frozenset(),
            post_game=True,
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert "sleep_talk" in result

    def test_returns_set_of_strings(self, db_with_tm_locations: Path) -> None:
        """Return type is set of strings."""
        config = LocationFilterConfig(
            accessible_locations=["Fallshore City"],
            available_hms=frozenset(),
        )
        result = get_available_tm_move_keys(config, db_path=db_with_tm_locations)
        assert result is not None
        assert isinstance(result, set)
        for key in result:
            assert isinstance(key, str)
