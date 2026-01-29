"""ABOUTME: Tests for the config module.
ABOUTME: Verifies sheets configuration loading and URL generation."""

from pathlib import Path

import pytest

from unbounddb.config import SheetsConfig, TabConfig, load_sheets_config


class TestSheetsConfig:
    """Tests for SheetsConfig class."""

    def test_get_export_url(self) -> None:
        """Export URL is correctly formatted."""
        config = SheetsConfig(
            spreadsheet_id="test123",
            tabs={"pokemon": TabConfig(gid="456", description="Test")},
        )

        url = config.get_export_url("pokemon")

        assert url == "https://docs.google.com/spreadsheets/d/test123/export?format=csv&gid=456"

    def test_get_export_url_unknown_tab(self) -> None:
        """Unknown tab raises KeyError."""
        config = SheetsConfig(
            spreadsheet_id="test123",
            tabs={"pokemon": TabConfig(gid="456", description="Test")},
        )

        with pytest.raises(KeyError):
            config.get_export_url("unknown")

    def test_get_tab_names(self) -> None:
        """Tab names are returned as list."""
        config = SheetsConfig(
            spreadsheet_id="test123",
            tabs={
                "pokemon": TabConfig(gid="1", description="Pokemon"),
                "moves": TabConfig(gid="2", description="Moves"),
            },
        )

        assert set(config.get_tab_names()) == {"pokemon", "moves"}


class TestLoadSheetsConfig:
    """Tests for load_sheets_config function."""

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_sheets_config(tmp_path / "nonexistent.yml")

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Valid YAML config is parsed correctly."""
        config_path = tmp_path / "sheets.yml"
        config_path.write_text("""
spreadsheet_id: "abc123"
tabs:
  pokemon:
    gid: "0"
    description: "Pokemon data"
  moves:
    gid: "123"
    description: "Move data"
""")

        config = load_sheets_config(config_path)

        assert config.spreadsheet_id == "abc123"
        assert len(config.tabs) == 2
        assert config.tabs["pokemon"].gid == "0"
        assert config.tabs["moves"].gid == "123"
