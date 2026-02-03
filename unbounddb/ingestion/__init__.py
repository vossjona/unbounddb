"""ABOUTME: Ingestion module for fetching data from external sources.
ABOUTME: Handles Google Sheets CSV downloads, GitHub files, and manual CSV validation."""

from unbounddb.ingestion.c_parser import (
    parse_base_stats_file,
    parse_learnsets_file,
)
from unbounddb.ingestion.evolution_parser import (
    parse_evolutions,
    parse_evolutions_file,
)
from unbounddb.ingestion.fetcher import (
    fetch_all_external_sources,
    fetch_all_github_sources,
    fetch_all_tabs,
    fetch_external_file,
    fetch_github_file,
    fetch_tab,
    load_external_config,
    load_github_config,
    validate_manual_csvs,
)
from unbounddb.ingestion.locations_parser import (
    parse_locations_csv,
)
from unbounddb.ingestion.showdown_parser import (
    parse_showdown_file,
    parse_showdown_file_to_dataframes,
)

__all__ = [
    "fetch_all_external_sources",
    "fetch_all_github_sources",
    "fetch_all_tabs",
    "fetch_external_file",
    "fetch_github_file",
    "fetch_tab",
    "load_external_config",
    "load_github_config",
    "parse_base_stats_file",
    "parse_evolutions",
    "parse_evolutions_file",
    "parse_learnsets_file",
    "parse_locations_csv",
    "parse_showdown_file",
    "parse_showdown_file_to_dataframes",
    "validate_manual_csvs",
]
