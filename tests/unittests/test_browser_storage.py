# ABOUTME: Tests for browser_storage.py pure helper functions.
# ABOUTME: Verifies parse_browser_data, upsert_profile, and remove_profile logic.

import json

from unbounddb.app.browser_storage import (
    parse_browser_data,
    remove_profile,
    upsert_profile,
)


class TestParseBrowserData:
    """Tests for parse_browser_data function."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        result = parse_browser_data(None)

        assert result is None

    def test_valid_dict_returns_profiles(self) -> None:
        """Valid dict with profiles key returns profile list."""
        raw = {
            "version": 1,
            "profiles": [{"name": "Run1", "progression_step": 5}],
        }

        result = parse_browser_data(raw)

        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "Run1"

    def test_valid_json_string_returns_profiles(self) -> None:
        """Valid JSON string is parsed into profile list."""
        raw = json.dumps(
            {
                "version": 1,
                "profiles": [{"name": "Run1", "active": True}],
            }
        )

        result = parse_browser_data(raw)

        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "Run1"

    def test_malformed_json_string_returns_none(self) -> None:
        """Malformed JSON string returns None."""
        result = parse_browser_data("{not valid json")

        assert result is None

    def test_missing_profiles_key_returns_none(self) -> None:
        """Dict without 'profiles' key returns None."""
        result = parse_browser_data({"version": 1})

        assert result is None

    def test_profiles_not_a_list_returns_none(self) -> None:
        """Dict with non-list 'profiles' value returns None."""
        result = parse_browser_data({"version": 1, "profiles": "not a list"})

        assert result is None

    def test_non_dict_non_string_returns_none(self) -> None:
        """Non-dict, non-string, non-None input returns None."""
        result = parse_browser_data(42)

        assert result is None

    def test_list_input_returns_none(self) -> None:
        """List input returns None (expects dict wrapper)."""
        result = parse_browser_data([{"name": "Run1"}])

        assert result is None

    def test_empty_profiles_list_returns_empty(self) -> None:
        """Dict with empty profiles list returns empty list."""
        result = parse_browser_data({"version": 1, "profiles": []})

        assert result is not None
        assert result == []

    def test_multiple_profiles(self) -> None:
        """Multiple profiles are all returned."""
        raw = {
            "version": 1,
            "profiles": [
                {"name": "Run1", "progression_step": 5},
                {"name": "Run2", "progression_step": 10},
            ],
        }

        result = parse_browser_data(raw)

        assert result is not None
        assert len(result) == 2


class TestUpsertProfile:
    """Tests for upsert_profile function."""

    def test_insert_into_empty_list(self) -> None:
        """Inserting into empty list adds the profile."""
        profile = {"name": "Run1", "progression_step": 5}

        result = upsert_profile([], profile)

        assert len(result) == 1
        assert result[0]["name"] == "Run1"

    def test_insert_new_profile(self) -> None:
        """New profile is appended to the list."""
        existing = [{"name": "Run1", "progression_step": 3}]
        new = {"name": "Run2", "progression_step": 7}

        result = upsert_profile(existing, new)

        assert len(result) == 2
        names = [p["name"] for p in result]
        assert "Run1" in names
        assert "Run2" in names

    def test_replace_existing_profile(self) -> None:
        """Existing profile is replaced by name."""
        existing = [
            {"name": "Run1", "progression_step": 3},
            {"name": "Run2", "progression_step": 7},
        ]
        updated = {"name": "Run1", "progression_step": 10}

        result = upsert_profile(existing, updated)

        assert len(result) == 2
        run1 = next(p for p in result if p["name"] == "Run1")
        assert run1["progression_step"] == 10

    def test_preserves_other_profiles(self) -> None:
        """Upserting one profile doesn't affect others."""
        existing = [
            {"name": "Run1", "progression_step": 3},
            {"name": "Run2", "progression_step": 7},
        ]
        updated = {"name": "Run1", "progression_step": 10}

        result = upsert_profile(existing, updated)

        run2 = next(p for p in result if p["name"] == "Run2")
        assert run2["progression_step"] == 7

    def test_does_not_mutate_original_list(self) -> None:
        """Original list is not mutated."""
        existing = [{"name": "Run1", "progression_step": 3}]
        original_len = len(existing)

        upsert_profile(existing, {"name": "Run2", "progression_step": 5})

        assert len(existing) == original_len


class TestRemoveProfile:
    """Tests for remove_profile function."""

    def test_remove_existing_profile(self) -> None:
        """Removes the named profile from the list."""
        profiles = [
            {"name": "Run1", "progression_step": 3},
            {"name": "Run2", "progression_step": 7},
        ]

        result = remove_profile(profiles, "Run1")

        assert len(result) == 1
        assert result[0]["name"] == "Run2"

    def test_remove_nonexistent_is_noop(self) -> None:
        """Removing a nonexistent name returns the same profiles."""
        profiles = [{"name": "Run1", "progression_step": 3}]

        result = remove_profile(profiles, "NonExistent")

        assert len(result) == 1
        assert result[0]["name"] == "Run1"

    def test_remove_from_empty_list(self) -> None:
        """Removing from empty list returns empty list."""
        result = remove_profile([], "Run1")

        assert result == []

    def test_does_not_mutate_original_list(self) -> None:
        """Original list is not mutated."""
        profiles = [
            {"name": "Run1", "progression_step": 3},
            {"name": "Run2", "progression_step": 7},
        ]
        original_len = len(profiles)

        remove_profile(profiles, "Run1")

        assert len(profiles) == original_len
