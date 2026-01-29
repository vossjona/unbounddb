"""ABOUTME: Configuration loaders for external data sources.
ABOUTME: Handles loading and parsing of sheets.yml configuration."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from unbounddb.settings import settings


class TabConfig(BaseModel):
    """Configuration for a single Google Sheets tab."""

    gid: str
    description: str


class SheetsConfig(BaseModel):
    """Configuration for Google Sheets data source."""

    spreadsheet_id: str
    tabs: dict[str, TabConfig]

    def get_export_url(self, tab_name: str) -> str:
        """Generate the CSV export URL for a given tab.

        Args:
            tab_name: Name of the tab as defined in the config.

        Returns:
            Full URL to download the tab as CSV.

        Raises:
            KeyError: If tab_name is not configured.
        """
        if tab_name not in self.tabs:
            raise KeyError(f"Tab '{tab_name}' not found in configuration")

        tab = self.tabs[tab_name]
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?format=csv&gid={tab.gid}"

    def get_tab_names(self) -> list[str]:
        """Return list of configured tab names."""
        return list(self.tabs.keys())


def load_sheets_config(config_path: Path | None = None) -> SheetsConfig:
    """Load sheets configuration from YAML file.

    Args:
        config_path: Path to the config file. Defaults to settings.sheets_config_path.

    Returns:
        Parsed SheetsConfig object.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is invalid.
    """
    if config_path is None:
        config_path = settings.sheets_config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Sheets config not found: {config_path}")

    with config_path.open() as f:
        raw_config = yaml.safe_load(f)

    return SheetsConfig.model_validate(raw_config)
