"""ABOUTME: Fetches data from Google Sheets exports and GitHub raw files.
ABOUTME: Supports async downloading with caching and manual CSV fallback."""

import asyncio
from pathlib import Path
from typing import Any

import httpx
import yaml

from unbounddb.config import SheetsConfig, load_sheets_config
from unbounddb.settings import settings

GITHUB_SOURCES_CONFIG = settings.project_root / "configs" / "github_sources.yml"


async def fetch_tab(
    tab_name: str,
    config: SheetsConfig,
    output_dir: Path,
    force: bool = False,
    client: httpx.AsyncClient | None = None,
) -> Path:
    """Fetch a single tab from Google Sheets as CSV.

    Args:
        tab_name: Name of the tab to fetch.
        config: Sheets configuration.
        output_dir: Directory to save the CSV file.
        force: If True, re-download even if file exists.
        client: Optional httpx client for connection reuse.

    Returns:
        Path to the downloaded CSV file.

    Raises:
        httpx.HTTPStatusError: If download fails.
        KeyError: If tab_name not in config.
    """
    output_path = output_dir / f"{tab_name}.csv"

    if output_path.exists() and not force:
        return output_path

    output_dir.mkdir(parents=True, exist_ok=True)

    url = config.get_export_url(tab_name)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        response = await client.get(url)
        response.raise_for_status()

        output_path.write_text(response.text, encoding="utf-8")
        return output_path
    finally:
        if should_close_client:
            await client.aclose()


async def fetch_all_tabs(
    config: SheetsConfig | None = None,
    output_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Path]:
    """Fetch all configured tabs from Google Sheets.

    Args:
        config: Sheets configuration. Loads default if not provided.
        output_dir: Directory to save CSV files. Uses settings default if not provided.
        force: If True, re-download even if files exist.

    Returns:
        Dictionary mapping tab names to their downloaded file paths.
    """
    if config is None:
        config = load_sheets_config()

    if output_dir is None:
        output_dir = settings.raw_exports_dir

    results: dict[str, Path] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        tasks = [fetch_tab(tab_name, config, output_dir, force, client) for tab_name in config.get_tab_names()]
        paths = await asyncio.gather(*tasks)

        results = dict(zip(config.get_tab_names(), paths, strict=True))

    return results


def validate_manual_csvs(
    tab_names: list[str] | None = None,
    manual_dir: Path | None = None,
) -> dict[str, Path]:
    """Validate that manual CSV files exist for all required tabs.

    Args:
        tab_names: List of tab names to check. Loads from config if not provided.
        manual_dir: Directory containing manual CSVs. Uses settings default if not provided.

    Returns:
        Dictionary mapping tab names to their file paths.

    Raises:
        FileNotFoundError: If any required CSV is missing.
    """
    if tab_names is None:
        config = load_sheets_config()
        tab_names = config.get_tab_names()

    if manual_dir is None:
        manual_dir = settings.raw_manual_dir

    results: dict[str, Path] = {}
    missing: list[str] = []

    for tab_name in tab_names:
        csv_path = manual_dir / f"{tab_name}.csv"
        if csv_path.exists():
            results[tab_name] = csv_path
        else:
            missing.append(tab_name)

    if missing:
        raise FileNotFoundError(f"Missing manual CSV files in {manual_dir}: {', '.join(missing)}")

    return results


def load_github_config() -> dict[str, Any]:
    """Load GitHub sources configuration.

    Returns:
        Dictionary with base_url and sources configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not GITHUB_SOURCES_CONFIG.exists():
        raise FileNotFoundError(f"GitHub sources config not found: {GITHUB_SOURCES_CONFIG}")

    with GITHUB_SOURCES_CONFIG.open() as f:
        return yaml.safe_load(f)


async def fetch_github_file(
    source_name: str,
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
    client: httpx.AsyncClient | None = None,
) -> Path:
    """Fetch a single file from GitHub raw.

    Args:
        source_name: Name of the source (e.g., 'pokemon', 'learnsets').
        config: GitHub config dict. Loads default if not provided.
        output_dir: Directory to save the file.
        force: If True, re-download even if file exists.
        client: Optional httpx client for connection reuse.

    Returns:
        Path to the downloaded file.

    Raises:
        httpx.HTTPStatusError: If download fails.
        KeyError: If source_name not in config.
    """
    if config is None:
        config = load_github_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir

    source = config["sources"][source_name]
    filename = source["file"]
    url = f"{config['base_url']}/{filename}"

    output_path = output_dir / filename

    if output_path.exists() and not force:
        return output_path

    output_dir.mkdir(parents=True, exist_ok=True)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        response = await client.get(url)
        response.raise_for_status()

        output_path.write_text(response.text, encoding="utf-8")
        return output_path
    finally:
        if should_close_client:
            await client.aclose()


async def fetch_all_github_sources(
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Path]:
    """Fetch all configured GitHub source files.

    Args:
        config: GitHub config dict. Loads default if not provided.
        output_dir: Directory to save files. Uses settings default if not provided.
        force: If True, re-download even if files exist.

    Returns:
        Dictionary mapping source names to their downloaded file paths.
    """
    if config is None:
        config = load_github_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir

    results: dict[str, Path] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        source_names = list(config["sources"].keys())
        tasks = [fetch_github_file(name, config, output_dir, force, client) for name in source_names]
        paths = await asyncio.gather(*tasks)

        results = dict(zip(source_names, paths, strict=True))

    return results
