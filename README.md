# Pokemon Unbound DB

A data tool for [Pokemon Unbound](https://www.pokecommunity.com/threads/pok%C3%A9mon-unbound-completed.382Pokemon) — browse Pokemon stats, plan battle strategies, and find catch locations.

## Features

- **Browse Tables** — View Pokemon stats, moves, learnsets, and more
- **Battle Analysis** — Analyze any trainer battle with defensive typing rankings, offensive type coverage, physical/special breakdowns, and per-Pokemon recommendations
- **Pokemon Ranker** — Find the best Pokemon to use against a specific battle, ranked by defensive typing, offensive moves, and stat alignment
- **Pokemon Locations** — Search where to catch any Pokemon, filtered by your game progress
- **Game Progress Profiles** — Save your progression and filter everything by what's actually available to you

## Data Sources

All data is parsed from the [Dynamic Pokemon Expansion](https://github.com/TheRealPokemon/DynamicPokemonExpansion) C source files and community-maintained Pokemon Unbound resources. Pokemon and all related properties belong to their respective owners.

## How It Works

The database is built on-demand from raw source files:

1. C source files (`Base_Stats.c`, `Learnsets.c`) are parsed with regex
2. Data is normalized into Polars DataFrames and written as Parquet files
3. Parquet files are loaded into a SQLite database
4. Streamlit serves the UI with live queries against SQLite

On Streamlit Cloud, the database builds automatically on first load (~30 seconds). Locally, you can build it manually or let the app auto-build.

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [GNU Make](https://www.gnu.org/software/make/)

### Setup

```bash
git clone https://github.com/vossjona/unbounddb.git
cd unbounddb
make setup
```

### Fetch Data & Build Database

```bash
uv run unbounddb fetch --github --verbose
uv run unbounddb build --github --verbose
```

### Run the App

```bash
uv run streamlit run streamlit_app.py
```

Or via the CLI:

```bash
uv run unbounddb ui
```

## Quality Checks

```bash
make format       # Ruff formatting
make lint         # Ruff linting
make typing       # MyPy type checking
make unittests    # Pytest unit tests
```

## Tech Stack

- **Data**: [Polars](https://pola.rs/) + [SQLite](https://sqlite.org/) + [PyArrow](https://arrow.apache.org/docs/python/)
- **UI**: [Streamlit](https://streamlit.io/)
- **Parsing**: Regex-based C struct parser
- **Config**: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **CLI**: [Typer](https://typer.tiangolo.com/)

## License

This is a fan project for personal use. Pokemon and all related properties are trademarks of their respective owners.
