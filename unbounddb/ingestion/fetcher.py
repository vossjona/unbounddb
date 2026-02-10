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
EXTERNAL_SOURCES_CONFIG = settings.project_root / "configs" / "external_sources.yml"


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

    if await asyncio.to_thread(output_path.exists) and not force:
        return output_path

    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

    url = config.get_export_url(tab_name)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        response = await client.get(url)
        response.raise_for_status()

        await asyncio.to_thread(output_path.write_text, response.text, encoding="utf-8")
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

    # Support either full 'url' or relative 'file' + base_url
    if "url" in source:
        url = source["url"]
        filename = Path(url).name
    else:
        filename = source["file"]
        url = f"{config['base_url']}/{filename}"

    output_path = output_dir / filename

    if await asyncio.to_thread(output_path.exists) and not force:
        return output_path

    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        response = await client.get(url)
        response.raise_for_status()

        await asyncio.to_thread(output_path.write_text, response.text, encoding="utf-8")
        return output_path
    finally:
        if should_close_client:
            await client.aclose()


HTTP_FORBIDDEN = 403
RATE_LIMIT_MAX_RETRIES = 3
RATE_LIMIT_BASE_DELAY = 60.0  # seconds


async def list_github_directory(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    path: str,
) -> list[dict[str, str]]:
    """List files in a GitHub directory using the API.

    Args:
        client: httpx client for making requests.
        owner: Repository owner (e.g., 'Skeli789').
        repo: Repository name (e.g., 'Dynamic-Pokemon-Expansion').
        branch: Branch name (e.g., 'Unbound').
        path: Directory path relative to repo root (e.g., 'src/tm_compatibility').

    Returns:
        List of dicts with 'name' and 'download_url' for each file.

    Raises:
        httpx.HTTPStatusError: If API request fails after all retries.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"

    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        response = await client.get(api_url)

        # Handle rate limiting with retry
        if response.status_code == HTTP_FORBIDDEN and "rate limit" in response.text.lower():
            if attempt < RATE_LIMIT_MAX_RETRIES:
                wait_time = RATE_LIMIT_BASE_DELAY * (2**attempt)  # Exponential backoff
                print(f"Rate limited. Waiting {wait_time:.0f}s before retry {attempt + 1}/{RATE_LIMIT_MAX_RETRIES}...")
                await asyncio.sleep(wait_time)
                continue
            raise httpx.HTTPStatusError(
                f"Rate limit exceeded after {RATE_LIMIT_MAX_RETRIES} retries",
                request=response.request,
                response=response,
            )

        response.raise_for_status()
        items = response.json()
        return [
            {"name": item["name"], "download_url": item["download_url"]} for item in items if item["type"] == "file"
        ]

    return []  # Should not reach here


async def fetch_github_directory(
    source_name: str,
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
    client: httpx.AsyncClient | None = None,
    rate_limit_delay: float = 0.1,
) -> list[Path]:
    """Fetch all files from a GitHub directory.

    Args:
        source_name: Name of the source in config (e.g., 'tm_compatibility').
        config: GitHub config dict. Loads default if not provided.
        output_dir: Base directory to save files. Uses settings default if not provided.
        force: If True, re-download even if files exist.
        client: Optional httpx client for connection reuse.
        rate_limit_delay: Delay in seconds between file downloads to avoid rate limits.

    Returns:
        List of paths to downloaded files.

    Raises:
        httpx.HTTPStatusError: If download fails.
        KeyError: If source_name not in config or missing 'directory' field.
    """
    if config is None:
        config = load_github_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir

    source = config["sources"][source_name]
    directory = source["directory"]

    # Parse base_url to extract owner, repo, branch
    # Format: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/src
    base_url = config["base_url"]
    parts = base_url.replace("https://raw.githubusercontent.com/", "").split("/")
    owner = parts[0]
    repo = parts[1]
    branch = parts[2]
    base_path = "/".join(parts[3:])  # e.g., "src"

    # Full path in repo
    full_path = f"{base_path}/{directory}" if base_path else directory

    # Create output subdirectory
    local_dir = output_dir / directory
    await asyncio.to_thread(local_dir.mkdir, parents=True, exist_ok=True)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        # List files in directory
        files = await list_github_directory(client, owner, repo, branch, full_path)

        downloaded_paths: list[Path] = []

        # Download files sequentially with delay to avoid rate limits
        # (raw.githubusercontent.com is less strict than API but still has limits)
        for file_info in files:
            filename = file_info["name"]
            download_url = file_info["download_url"]
            local_path = local_dir / filename

            if await asyncio.to_thread(local_path.exists) and not force:
                downloaded_paths.append(local_path)
                continue

            response = await client.get(download_url)
            response.raise_for_status()
            await asyncio.to_thread(local_path.write_text, response.text, encoding="utf-8")
            downloaded_paths.append(local_path)

            # Small delay to avoid rate limiting
            await asyncio.sleep(rate_limit_delay)

        return downloaded_paths
    finally:
        if should_close_client:
            await client.aclose()


async def fetch_all_github_sources(
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Path | list[Path]]:
    """Fetch all configured GitHub source files and directories.

    Args:
        config: GitHub config dict. Loads default if not provided.
        output_dir: Directory to save files. Uses settings default if not provided.
        force: If True, re-download even if files exist.

    Returns:
        Dictionary mapping source names to their downloaded file paths.
        For directory sources, the value is a list of paths.
    """
    if config is None:
        config = load_github_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir

    results: dict[str, Path | list[Path]] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        # Separate file sources from directory sources
        file_sources = []
        dir_sources = []
        for name, source in config["sources"].items():
            if "directory" in source:
                dir_sources.append(name)
            else:
                file_sources.append(name)

        # Fetch all file sources (these use raw.githubusercontent.com, not API)
        file_tasks = [fetch_github_file(name, config, output_dir, force, client) for name in file_sources]
        file_paths = await asyncio.gather(*file_tasks)
        results.update(dict(zip(file_sources, file_paths, strict=True)))

        # Fetch directory sources sequentially to avoid API rate limits
        # (each directory listing requires a GitHub API call)
        for dir_name in dir_sources:
            # Add delay before each API call to avoid rate limiting
            await asyncio.sleep(1.0)
            try:
                dir_paths = await fetch_github_directory(dir_name, config, output_dir, force, client)
                results[dir_name] = dir_paths
            except httpx.HTTPStatusError as e:
                if "rate limit" in str(e).lower():
                    print(f"Warning: Skipping {dir_name} due to rate limit. Run again later to fetch.")
                else:
                    raise

    return results


def load_external_config() -> dict[str, Any]:
    """Load external sources configuration.

    Returns:
        Dictionary with sources configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not EXTERNAL_SOURCES_CONFIG.exists():
        raise FileNotFoundError(f"External sources config not found: {EXTERNAL_SOURCES_CONFIG}")

    with EXTERNAL_SOURCES_CONFIG.open() as f:
        return yaml.safe_load(f)


async def fetch_external_file(
    source_name: str,
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
    client: httpx.AsyncClient | None = None,
) -> Path:
    """Fetch a single file from an external URL.

    Args:
        source_name: Name of the source (e.g., 'trainers').
        config: External config dict. Loads default if not provided.
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
        config = load_external_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir  # Store in same raw directory

    source = config["sources"][source_name]
    url = source["url"]

    # Use source name as filename with appropriate extension
    # CSV exports from Google Sheets use .csv extension
    extension = ".csv" if "format=csv" in url else ".txt"
    filename = f"{source_name}{extension}"
    output_path = output_dir / filename

    if await asyncio.to_thread(output_path.exists) and not force:
        return output_path

    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        response = await client.get(url)
        response.raise_for_status()

        await asyncio.to_thread(output_path.write_text, response.text, encoding="utf-8")
        return output_path
    finally:
        if should_close_client:
            await client.aclose()


async def fetch_all_external_sources(
    config: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Path]:
    """Fetch all configured external source files.

    Args:
        config: External config dict. Loads default if not provided.
        output_dir: Directory to save files. Uses settings default if not provided.
        force: If True, re-download even if files exist.

    Returns:
        Dictionary mapping source names to their downloaded file paths.
    """
    if config is None:
        config = load_external_config()

    if output_dir is None:
        output_dir = settings.raw_github_dir

    results: dict[str, Path] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        source_names = list(config["sources"].keys())
        tasks = [fetch_external_file(name, config, output_dir, force, client) for name in source_names]
        paths = await asyncio.gather(*tasks)

        results = dict(zip(source_names, paths, strict=True))

    return results
