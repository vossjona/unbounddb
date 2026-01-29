"""ABOUTME: Ingestion module for fetching data from external sources.
ABOUTME: Handles Google Sheets CSV downloads, GitHub files, and manual CSV validation."""

from unbounddb.ingestion.c_parser import (
    parse_base_stats_file,
    parse_learnsets_file,
)
from unbounddb.ingestion.fetcher import (
    fetch_all_github_sources,
    fetch_all_tabs,
    fetch_github_file,
    fetch_tab,
    load_github_config,
    validate_manual_csvs,
)

__all__ = [
    "fetch_all_github_sources",
    "fetch_all_tabs",
    "fetch_github_file",
    "fetch_tab",
    "load_github_config",
    "parse_base_stats_file",
    "parse_learnsets_file",
    "validate_manual_csvs",
]
