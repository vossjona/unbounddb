"""ABOUTME: Text normalization utilities for consistent key generation.
ABOUTME: Provides slugify function for creating join keys from names."""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to a normalized slug for use as a join key.

    Handles:
    - Unicode normalization (accents, special chars)
    - Whitespace trimming and collapsing
    - Lowercase conversion
    - Special character removal
    - Hyphen/underscore to underscore

    Args:
        text: Input text to slugify.

    Returns:
        Normalized slug string.

    Examples:
        >>> slugify("Pikachu")
        'pikachu'
        >>> slugify("Mr. Mime")
        'mr_mime'
        >>> slugify("Nidoran (F)")
        'nidoran_f'
        >>> slugify("  Farfetch'd  ")
        'farfetchd'
    """
    if not text:
        return ""

    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    text = text.lower()

    # Replace common separators with underscore
    text = re.sub(r"[-\s]+", "_", text)

    # Remove characters that aren't alphanumeric or underscore
    text = re.sub(r"[^a-z0-9_]", "", text)

    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text)

    # Strip leading/trailing underscores
    text = text.strip("_")

    return text
