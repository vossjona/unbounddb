# ABOUTME: Unit tests for the Advanced Move Search feature.
# ABOUTME: Tests filter dataclass and query function.

import sqlite3
from pathlib import Path

import pytest

from unbounddb.app.move_search_filters import MoveSearchFilters
from unbounddb.app.queries import search_moves_advanced


class TestMoveSearchFiltersDefaults:
    """Tests for MoveSearchFilters default values."""

    def test_default_creates_empty_filter(self) -> None:
        f = MoveSearchFilters()
        assert f.move_types == ()
        assert f.categories == ()
        assert f.power_min is None
        assert f.stab_only is False
        assert f.available_pokemon is None

    def test_frozen_and_hashable(self) -> None:
        f = MoveSearchFilters()
        hash(f)  # Must not raise

    def test_custom_values(self) -> None:
        f = MoveSearchFilters(
            move_types=("Fire", "Ghost"),
            categories=("Special",),
            power_min=80,
            stab_only=True,
            min_bst=400,
        )
        assert f.move_types == ("Fire", "Ghost")
        assert f.power_min == 80


@pytest.fixture
def move_search_db(tmp_path: Path) -> Path:
    """Create a test database with pokemon, moves, and pokemon_moves tables."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))

    conn.execute("""
        CREATE TABLE pokemon (
            name TEXT, pokemon_key TEXT,
            hp INTEGER, attack INTEGER, defense INTEGER,
            sp_attack INTEGER, sp_defense INTEGER, speed INTEGER, bst INTEGER,
            type1 TEXT, type2 TEXT,
            ability1 TEXT, ability2 TEXT, hidden_ability TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO pokemon VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("Gengar", "gengar", 60, 65, 60, 130, 75, 110, 500, "Ghost", "Poison", "Cursed Body", None, None),
            (
                "Alakazam",
                "alakazam",
                55,
                50,
                45,
                135,
                95,
                120,
                500,
                "Psychic",
                None,
                "Synchronize",
                "Inner Focus",
                "Magic Guard",
            ),
            ("Machamp", "machamp", 90, 130, 80, 65, 85, 55, 505, "Fighting", None, "Guts", "No Guard", "Steadfast"),
        ],
    )

    conn.execute("""
        CREATE TABLE moves (
            name TEXT, move_key TEXT, type TEXT, category TEXT,
            power INTEGER, accuracy INTEGER, pp INTEGER, priority INTEGER,
            effect TEXT, has_secondary_effect INTEGER,
            makes_contact INTEGER, is_sound_move INTEGER,
            is_punch_move INTEGER, is_bite_move INTEGER, is_pulse_move INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO moves VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("Shadow Ball", "shadow_ball", "Ghost", "Special", 80, 100, 15, 0, None, 1, 0, 0, 0, 0, 0),
            ("Psychic", "psychic", "Psychic", "Special", 90, 100, 10, 0, None, 1, 0, 0, 0, 0, 0),
            ("Close Combat", "close_combat", "Fighting", "Physical", 120, 100, 5, 0, None, 0, 1, 0, 0, 0, 0),
            ("Sludge Bomb", "sludge_bomb", "Poison", "Special", 90, 100, 10, 0, None, 1, 0, 0, 0, 0, 0),
            ("Thunder Punch", "thunder_punch", "Electric", "Physical", 75, 100, 15, 0, None, 1, 1, 0, 1, 0, 0),
        ],
    )

    conn.execute("""
        CREATE TABLE pokemon_moves (
            pokemon_key TEXT, move_key TEXT, learn_method TEXT, level INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO pokemon_moves VALUES (?,?,?,?)",
        [
            ("gengar", "shadow_ball", "level", 28),
            ("gengar", "sludge_bomb", "tm", None),
            ("alakazam", "psychic", "level", 30),
            ("machamp", "close_combat", "level", 42),
            ("machamp", "thunder_punch", "tutor", None),
        ],
    )

    conn.commit()
    conn.close()
    return db_path


class TestSearchMovesAdvancedNoFilters:
    """Tests for base query with no filters applied."""

    def test_returns_all_pokemon_move_combinations(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(), db_path=move_search_db)
        assert len(results) == 5

    def test_result_contains_expected_keys(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(), db_path=move_search_db)
        required = {
            "pokemon_name",
            "pokemon_key",
            "pokemon_type1",
            "pokemon_type2",
            "hp",
            "attack",
            "defense",
            "sp_attack",
            "sp_defense",
            "speed",
            "bst",
            "ability1",
            "ability2",
            "hidden_ability",
            "move_name",
            "move_key",
            "move_type",
            "category",
            "power",
            "accuracy",
            "pp",
            "priority",
            "makes_contact",
            "is_sound_move",
            "is_punch_move",
            "is_bite_move",
            "is_pulse_move",
            "has_secondary_effect",
            "learn_method",
            "level",
            "is_stab",
        }
        for row in results:
            assert required.issubset(row.keys())

    def test_stab_calculated_correctly(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(), db_path=move_search_db)
        gengar_shadow = next(r for r in results if r["pokemon_key"] == "gengar" and r["move_key"] == "shadow_ball")
        assert gengar_shadow["is_stab"] is True  # Ghost on Ghost
        gengar_sludge = next(r for r in results if r["pokemon_key"] == "gengar" and r["move_key"] == "sludge_bomb")
        assert gengar_sludge["is_stab"] is True  # Poison on Poison (type2)
        machamp_punch = next(r for r in results if r["pokemon_key"] == "machamp" and r["move_key"] == "thunder_punch")
        assert machamp_punch["is_stab"] is False  # Electric on Fighting

    def test_ordered_by_bst_desc(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(), db_path=move_search_db)
        bst_values = [r["bst"] for r in results]
        assert bst_values[0] >= bst_values[-1]


class TestSearchMovesAdvancedMoveFilters:
    """Tests for move-level filters (type, category, power, flags)."""

    def test_filter_by_move_type(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_types=("Ghost",)), db_path=move_search_db)
        assert all(r["move_type"] == "Ghost" for r in results)
        assert len(results) == 1

    def test_filter_by_multiple_types(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_types=("Ghost", "Psychic")), db_path=move_search_db)
        assert len(results) == 2

    def test_filter_by_category(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(categories=("Physical",)), db_path=move_search_db)
        assert all(r["category"] == "Physical" for r in results)
        assert len(results) == 2

    def test_filter_power_min(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(power_min=90), db_path=move_search_db)
        assert all(r["power"] >= 90 for r in results)

    def test_filter_power_range(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(power_min=80, power_max=100), db_path=move_search_db)
        assert all(80 <= r["power"] <= 100 for r in results)

    def test_filter_makes_contact(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(makes_contact=True), db_path=move_search_db)
        assert all(r["makes_contact"] for r in results)
        assert {r["move_name"] for r in results} == {"Close Combat", "Thunder Punch"}

    def test_filter_is_punch_move(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(is_punch_move=True), db_path=move_search_db)
        assert len(results) == 1
        assert results[0]["move_name"] == "Thunder Punch"

    def test_filter_by_move_name(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_names=("Shadow Ball",)), db_path=move_search_db)
        assert len(results) == 1
        assert results[0]["move_name"] == "Shadow Ball"

    def test_filter_by_multiple_move_names(self, move_search_db: Path) -> None:
        results = search_moves_advanced(
            MoveSearchFilters(move_names=("Shadow Ball", "Psychic")), db_path=move_search_db
        )
        assert len(results) == 2
        assert {r["move_name"] for r in results} == {"Shadow Ball", "Psychic"}

    def test_empty_move_names_means_no_filter(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_names=()), db_path=move_search_db)
        assert len(results) == 5

    def test_empty_types_tuple_means_no_filter(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_types=()), db_path=move_search_db)
        assert len(results) == 5


class TestSearchMovesAdvancedPokemonFilters:
    """Tests for Pokemon, learn-method, and stat filters."""

    def test_filter_learn_method(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(learn_methods=("level",)), db_path=move_search_db)
        assert all(r["learn_method"] == "level" for r in results)

    def test_filter_max_learn_level_excludes_high_level_moves(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(max_learn_level=30), db_path=move_search_db)
        for r in results:
            if r["learn_method"] == "level":
                assert r["level"] <= 30
        # Machamp Close Combat (level 42) excluded, but Thunder Punch (tutor) stays
        keys = {(r["pokemon_key"], r["move_key"]) for r in results}
        assert ("machamp", "close_combat") not in keys
        assert ("machamp", "thunder_punch") in keys

    def test_filter_stab_only(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(stab_only=True), db_path=move_search_db)
        assert all(r["is_stab"] is True for r in results)
        assert ("machamp", "thunder_punch") not in {(r["pokemon_key"], r["move_key"]) for r in results}

    def test_filter_min_bst(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(min_bst=505), db_path=move_search_db)
        assert all(r["pokemon_key"] == "machamp" for r in results)

    def test_filter_min_sp_attack(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(min_sp_attack=130), db_path=move_search_db)
        assert {r["pokemon_key"] for r in results} == {"gengar", "alakazam"}


class TestSearchMovesAdvancedGameProgress:
    """Tests for game progress filters (available Pokemon and TMs)."""

    def test_filter_available_pokemon(self, move_search_db: Path) -> None:
        results = search_moves_advanced(
            MoveSearchFilters(available_pokemon=frozenset({"Gengar"})), db_path=move_search_db
        )
        assert all(r["pokemon_name"] == "Gengar" for r in results)
        assert len(results) == 2

    def test_available_pokemon_none_means_all(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(available_pokemon=None), db_path=move_search_db)
        assert len(results) == 5

    def test_available_pokemon_empty_returns_empty(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(available_pokemon=frozenset()), db_path=move_search_db)
        assert results == []

    def test_filter_available_tm_keys(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(available_tm_keys=frozenset()), db_path=move_search_db)
        # Gengar sludge_bomb (tm) excluded, 4 remain
        assert len(results) == 4
        assert all(r["learn_method"] != "tm" for r in results)

    def test_available_tm_keys_none_means_all(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(available_tm_keys=None), db_path=move_search_db)
        assert len(results) == 5


class TestSearchMovesAdvancedCombined:
    """Tests for combined filters composing with AND logic."""

    def test_type_and_category(self, move_search_db: Path) -> None:
        results = search_moves_advanced(
            MoveSearchFilters(move_types=("Ghost",), categories=("Special",)), db_path=move_search_db
        )
        assert len(results) == 1
        assert results[0]["move_name"] == "Shadow Ball"

    def test_power_and_stab(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(power_min=90, stab_only=True), db_path=move_search_db)
        # Sludge Bomb (Gengar STAB), Psychic (Alakazam STAB), Close Combat (Machamp STAB)
        assert len(results) == 3

    def test_stat_and_learn_method(self, move_search_db: Path) -> None:
        results = search_moves_advanced(
            MoveSearchFilters(min_speed=100, learn_methods=("level",)), db_path=move_search_db
        )
        assert {r["pokemon_key"] for r in results} == {"gengar", "alakazam"}

    def test_no_results_returns_empty(self, move_search_db: Path) -> None:
        results = search_moves_advanced(MoveSearchFilters(move_types=("Fairy",)), db_path=move_search_db)
        assert results == []
