"""ABOUTME: Configuration logic and path settings for the project.
ABOUTME: Provides paths for data directories, configs, and database files."""

from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings

from unbounddb import __version__


def _get_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Contains settings for this project."""

    VERSION: str = __version__
    """Project version."""

    PROJECT_ROOT: Path = _get_project_root()
    """Root directory of the project."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def project_root(self) -> Path:
        """Root directory of the project (alias for PROJECT_ROOT)."""
        return self.PROJECT_ROOT

    @computed_field  # type: ignore[prop-decorator]
    @property
    def data_dir(self) -> Path:
        """Base data directory."""
        return self.PROJECT_ROOT / "data"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def raw_exports_dir(self) -> Path:
        """Directory for downloaded CSV exports from Google Sheets."""
        return self.data_dir / "raw" / "exports"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def raw_manual_dir(self) -> Path:
        """Directory for manually placed CSV files."""
        return self.data_dir / "raw" / "manual"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def raw_github_dir(self) -> Path:
        """Directory for downloaded files from GitHub."""
        return self.data_dir / "raw" / "github"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def curated_dir(self) -> Path:
        """Directory for curated Parquet files."""
        return self.data_dir / "curated"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_path(self) -> Path:
        """Path to the SQLite database file."""
        return self.data_dir / "db" / "unbound.sqlite"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def user_db_path(self) -> Path:
        """Path to the user data SQLite database file."""
        return self.data_dir / "db" / "user_data.sqlite"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def configs_dir(self) -> Path:
        """Directory containing configuration files."""
        return self.PROJECT_ROOT / "configs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sheets_config_path(self) -> Path:
        """Path to the sheets.yml configuration file."""
        return self.configs_dir / "sheets.yml"


settings = Settings()
