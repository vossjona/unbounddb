"""ABOUTME: Tests for the normalize module.
ABOUTME: Verifies slugify function behavior for key generation."""

import pytest

from unbounddb.build.normalize import slugify


class TestSlugify:
    """Tests for slugify function."""

    def test_simple_lowercase(self) -> None:
        """Simple names become lowercase."""
        assert slugify("Pikachu") == "pikachu"

    def test_spaces_become_underscores(self) -> None:
        """Spaces are converted to underscores."""
        assert slugify("Mr. Mime") == "mr_mime"

    def test_parentheses_handled(self) -> None:
        """Parentheses are removed and contents preserved."""
        assert slugify("Nidoran (F)") == "nidoran_f"

    def test_apostrophe_removed(self) -> None:
        """Apostrophes are removed."""
        assert slugify("Farfetch'd") == "farfetchd"

    def test_whitespace_trimmed(self) -> None:
        """Leading/trailing whitespace is trimmed."""
        assert slugify("  Bulbasaur  ") == "bulbasaur"

    def test_multiple_spaces_collapsed(self) -> None:
        """Multiple spaces become single underscore."""
        assert slugify("Tapu  Koko") == "tapu_koko"

    def test_hyphens_become_underscores(self) -> None:
        """Hyphens are converted to underscores."""
        assert slugify("Ho-Oh") == "ho_oh"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert slugify("") == ""

    def test_unicode_normalized(self) -> None:
        """Unicode characters are normalized to ASCII."""
        assert slugify("Flabébé") == "flabebe"

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("Thunderbolt", "thunderbolt"),
            ("Thunder Wave", "thunder_wave"),
            ("Self-Destruct", "self_destruct"),
            ("Double-Edge", "double_edge"),
        ],
    )
    def test_move_names(self, input_text: str, expected: str) -> None:
        """Various move name formats are handled correctly."""
        assert slugify(input_text) == expected
