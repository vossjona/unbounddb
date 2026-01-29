# CLAUDE.md - Project Guidelines

This file provides project-specific guidance for the UnboundDB codebase.

## Project Overview

UnboundDB is a data pipeline and query tool for Pokemon Unbound game data. It:
1. Fetches Pokemon data from GitHub C source files (Dynamic Pokemon Expansion repo)
2. Parses C structs to extract stats, types, abilities, and learnsets
3. Normalizes data and loads into DuckDB via Polars/Parquet
4. Exposes a Streamlit UI for querying Pokemon by type and move

### Data Flow

```
GitHub C Files → C Parser → Polars DataFrame → Parquet → DuckDB → Streamlit UI
```

### Key Components

| Module | Purpose |
|--------|---------|
| `unbounddb/ingestion/c_parser.py` | Parses Base_Stats.c and Learnsets.c |
| `unbounddb/ingestion/fetcher.py` | Fetches from GitHub raw URLs |
| `unbounddb/build/pipeline.py` | Orchestrates CSV/C → Parquet → DuckDB |
| `unbounddb/build/normalize.py` | `slugify()` for generating join keys |
| `unbounddb/app/main.py` | Streamlit UI |
| `unbounddb/app/queries.py` | DuckDB query functions |
| `unbounddb/cli.py` | Typer CLI entry point |

## CLI Commands

```bash
# Fetch data from GitHub C source files
unbounddb fetch --github --verbose

# Build DuckDB database from fetched files
unbounddb build --github --verbose

# Launch Streamlit UI
unbounddb ui --port 8501
```

## Data Sources

Primary data comes from GitHub C source files (not Google Sheets):
- `Base_Stats.c` → Pokemon stats, types, abilities (1,274 Pokemon)
- `Learnsets.c` → Level-up move learnsets (16,976 entries)

See `docs/links.md` for all data source URLs.

## Database Schema

Three tables in DuckDB:

**pokemon**: name, hp, attack, defense, sp_attack, sp_defense, speed, bst, type1, type2, ability1, ability2, hidden_ability, pokemon_key

**learnsets**: pokemon, move, level, pokemon_key, move_key

**moves**: move, move_key (extracted from learnsets)

Join on `pokemon_key` and `move_key` (slugified names).

## PYTHON-SPECIFIC STANDARDS

### Type Hints & Annotations

- **Required on all functions**: Return types and all parameters
- **Use | for unions**: `type | None` for nullable values
- **Generic types**: `list[str]`, `dict[str, Any]` (not `List`, `Dict`)
- **Callable types**: Use `Callable[[Args], Return]` from typing

### Async Patterns

- HTTP fetching uses `httpx.AsyncClient` with `asyncio.gather()` for parallel downloads
- CLI uses `asyncio.run()` to bridge sync Typer with async fetchers

### Code Organization

- **Import order**: Standard library → Third-party → Local imports
- **Use `__all__` in `__init__.py`**: Explicitly export public APIs
- **Google-style docstrings**: Required for all public functions
- **ABOUTME comments**: All files start with 2-line ABOUTME comments

## CRITICAL IMPLEMENTATION PATTERNS

### Slugify for Join Keys

All joins use slugified names as keys:
```python
from unbounddb.build.normalize import slugify

# "Thunder Wave" → "thunder_wave"
# "Nidoran (F)" → "nidoran_f"
# "Farfetch'd" → "farfetchd"
```

### C Parser Pattern

The C parser uses regex to extract struct fields:
```python
species_pattern = re.compile(r"\[SPECIES_(\w+)\]\s*=\s*\{([^}]+)\}")
field_patterns = {"baseHP": re.compile(r"\.baseHP\s*=\s*(\d+)")}
```

### Polars DataFrame Operations

```python
import polars as pl

df = df.with_columns(
    pl.col("name").map_elements(slugify, return_dtype=pl.String).alias("pokemon_key")
)
```

### DuckDB Queries

Use parameterized queries for user input:
```python
result = conn.execute("SELECT * FROM pokemon WHERE type1 = ?", [pokemon_type]).pl()
```

Column names from schema introspection are safe to use in f-strings (add `# noqa: S608`).

## TESTING STRATEGY

- **Unit tests** (`tests/unittests/`): Test pure functions (slugify, config loading)
- **No mocking without permission**: Never mock unless explicitly allowed
- **Parametrized tests**: Use `@pytest.mark.parametrize` for multiple inputs

```bash
make unittests          # Run unit tests only
```

## QUALITY CHECKS

All must pass before committing:

```bash
make format      # Ruff formatting
make lint        # Ruff linting
make typing      # MyPy type checking
make unittests   # Unit tests
```

Or use pre-commit: `pre-commit run`

## CONFIGURATION

### Settings (unbounddb/settings.py)

Uses `pydantic_settings.BaseSettings` with computed properties:
- `settings.raw_github_dir` → `data/raw/github/`
- `settings.curated_dir` → `data/curated/`
- `settings.db_path` → `data/db/unbound.duckdb`

### GitHub Sources (configs/github_sources.yml)

Maps source names to GitHub raw file URLs.

## DEFINITION OF DONE

Code is complete when ALL pass:

- ✅ `make format` - Code formatting
- ✅ `make lint` - Linting checks
- ✅ `make typing` - Type checking
- ✅ `make unittests` - Unit tests
- ✅ Feature works end-to-end
- ✅ Old code removed
- ✅ Public functions have docstrings
- ✅ Files have ABOUTME comments