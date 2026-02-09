# ABOUTME: Tests for user_database.py DuckDB operations.
# ABOUTME: Verifies CRUD operations for profile storage with progression step schema.

from pathlib import Path

import pytest

from unbounddb.app.user_database import (
    create_profile,
    delete_profile,
    get_active_profile,
    get_profile,
    get_profile_count,
    get_user_connection,
    list_profiles,
    profile_exists,
    set_active_profile,
    update_profile,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    db_path = tmp_path / "db" / "test_user_data.duckdb"
    return db_path


class TestGetUserConnection:
    """Tests for get_user_connection function."""

    def test_creates_database_file(self, temp_db: Path) -> None:
        """Connection creates the database file if it doesn't exist."""
        conn = get_user_connection(temp_db)
        conn.close()

        assert temp_db.exists()

    def test_creates_profiles_table(self, temp_db: Path) -> None:
        """Connection creates the profiles table."""
        conn = get_user_connection(temp_db)

        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        conn.close()

        assert "profiles" in table_names


class TestCreateProfile:
    """Tests for create_profile function."""

    def test_create_profile_success(self, temp_db: Path) -> None:
        """Creating a new profile returns True."""
        result = create_profile("jonas", temp_db)

        assert result is True

    def test_create_profile_duplicate_fails(self, temp_db: Path) -> None:
        """Creating a duplicate profile returns False."""
        create_profile("jonas", temp_db)
        result = create_profile("jonas", temp_db)

        assert result is False

    def test_created_profile_has_defaults(self, temp_db: Path) -> None:
        """New profiles have default values."""
        create_profile("jonas", temp_db)
        data = get_profile("jonas", temp_db)

        assert data is not None
        assert data["progression_step"] == 0
        assert data["rod_level"] == "None"
        assert data["difficulty"] is None
        assert data["active"] is False


class TestListProfiles:
    """Tests for list_profiles function."""

    def test_empty_database_returns_empty_list(self, temp_db: Path) -> None:
        """Empty database returns empty list."""
        result = list_profiles(temp_db)

        assert result == []

    def test_returns_profile_names_sorted(self, temp_db: Path) -> None:
        """Returns profile names in sorted order."""
        create_profile("tim", temp_db)
        create_profile("alice", temp_db)
        create_profile("jonas", temp_db)

        result = list_profiles(temp_db)

        assert result == ["alice", "jonas", "tim"]


class TestGetProfile:
    """Tests for get_profile function."""

    def test_nonexistent_profile_returns_none(self, temp_db: Path) -> None:
        """Getting nonexistent profile returns None."""
        result = get_profile("nonexistent", temp_db)

        assert result is None

    def test_returns_all_fields(self, temp_db: Path) -> None:
        """Returns all profile fields."""
        create_profile("jonas", temp_db)
        update_profile("jonas", temp_db, progression_step=5, difficulty="Expert")

        data = get_profile("jonas", temp_db)

        assert data is not None
        assert data["name"] == "jonas"
        assert data["progression_step"] == 5
        assert data["difficulty"] == "Expert"
        assert data["rod_level"] == "None"


class TestUpdateProfile:
    """Tests for update_profile function."""

    def test_update_single_field(self, temp_db: Path) -> None:
        """Updating a single field works."""
        create_profile("jonas", temp_db)
        update_profile("jonas", temp_db, progression_step=3)

        data = get_profile("jonas", temp_db)

        assert data is not None
        assert data["progression_step"] == 3

    def test_update_multiple_fields(self, temp_db: Path) -> None:
        """Updating multiple fields at once works."""
        create_profile("jonas", temp_db)
        update_profile("jonas", temp_db, progression_step=10, rod_level="Good Rod", difficulty="Insane")

        data = get_profile("jonas", temp_db)

        assert data is not None
        assert data["progression_step"] == 10
        assert data["rod_level"] == "Good Rod"
        assert data["difficulty"] == "Insane"

    def test_update_nonexistent_profile_returns_false(self, temp_db: Path) -> None:
        """Updating nonexistent profile returns False."""
        result = update_profile("nonexistent", temp_db, progression_step=1)

        assert result is False

    def test_update_ignores_invalid_fields(self, temp_db: Path) -> None:
        """Invalid fields are ignored."""
        create_profile("jonas", temp_db)
        # This should not raise an error
        result = update_profile("jonas", temp_db, invalid_field="value")

        assert result is False  # No valid fields to update


class TestDeleteProfile:
    """Tests for delete_profile function."""

    def test_delete_existing_profile(self, temp_db: Path) -> None:
        """Deleting existing profile returns True."""
        create_profile("jonas", temp_db)
        result = delete_profile("jonas", temp_db)

        assert result is True
        assert profile_exists("jonas", temp_db) is False

    def test_delete_nonexistent_profile(self, temp_db: Path) -> None:
        """Deleting nonexistent profile returns False."""
        result = delete_profile("nonexistent", temp_db)

        assert result is False


class TestActiveProfile:
    """Tests for get/set active profile functions."""

    def test_no_active_profile_by_default(self, temp_db: Path) -> None:
        """No active profile initially."""
        create_profile("jonas", temp_db)
        result = get_active_profile(temp_db)

        assert result is None

    def test_set_active_profile(self, temp_db: Path) -> None:
        """Setting active profile works."""
        create_profile("jonas", temp_db)
        set_active_profile("jonas", temp_db)

        result = get_active_profile(temp_db)

        assert result == "jonas"

    def test_set_active_profile_clears_previous(self, temp_db: Path) -> None:
        """Setting new active profile clears the previous one."""
        create_profile("jonas", temp_db)
        create_profile("tim", temp_db)

        set_active_profile("jonas", temp_db)
        set_active_profile("tim", temp_db)

        result = get_active_profile(temp_db)

        assert result == "tim"

        # Verify jonas is no longer active
        jonas_data = get_profile("jonas", temp_db)
        assert jonas_data is not None
        assert jonas_data["active"] is False

    def test_set_active_profile_to_none(self, temp_db: Path) -> None:
        """Setting active profile to None clears all."""
        create_profile("jonas", temp_db)
        set_active_profile("jonas", temp_db)
        set_active_profile(None, temp_db)

        result = get_active_profile(temp_db)

        assert result is None


class TestProfileExists:
    """Tests for profile_exists function."""

    def test_existing_profile_returns_true(self, temp_db: Path) -> None:
        """Existing profile returns True."""
        create_profile("jonas", temp_db)

        assert profile_exists("jonas", temp_db) is True

    def test_nonexistent_profile_returns_false(self, temp_db: Path) -> None:
        """Nonexistent profile returns False."""
        assert profile_exists("nonexistent", temp_db) is False


class TestGetProfileCount:
    """Tests for get_profile_count function."""

    def test_empty_database_returns_zero(self, temp_db: Path) -> None:
        """Empty database returns 0."""
        result = get_profile_count(temp_db)

        assert result == 0

    def test_returns_correct_count(self, temp_db: Path) -> None:
        """Returns correct profile count."""
        create_profile("jonas", temp_db)
        create_profile("tim", temp_db)
        create_profile("alice", temp_db)

        result = get_profile_count(temp_db)

        assert result == 3
