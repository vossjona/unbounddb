"""ABOUTME: Build pipeline orchestration for CSV to DuckDB transformation.
ABOUTME: Coordinates reading CSVs, transforming to Parquet, and loading to database."""

from collections.abc import Callable
from pathlib import Path

import polars as pl

from unbounddb.build.database import create_database, create_indexes, load_parquet_to_table
from unbounddb.build.normalize import slugify
from unbounddb.build.transformers import get_transformer
from unbounddb.config import load_sheets_config
from unbounddb.ingestion.c_parser import (
    parse_base_stats_file,
    parse_learnsets_file,
    parse_moves_info_file,
)
from unbounddb.ingestion.egg_moves_parser import parse_egg_moves_file
from unbounddb.ingestion.evolution_parser import parse_evolutions_file
from unbounddb.ingestion.locations_parser import parse_locations_csv
from unbounddb.ingestion.tm_tutor_parser import parse_tm_tutor_directory
from unbounddb.settings import settings

LogFunc = Callable[[str], None]


def _parse_pokemon(source_dir: Path, curated_dir: Path, log: LogFunc) -> tuple[str, Path] | None:
    """Parse Base_Stats.c to pokemon parquet."""
    base_stats_path = source_dir / "Base_Stats.c"
    if not base_stats_path.exists():
        log(f"Warning: Base_Stats.c not found at {base_stats_path}")
        return None

    log("Parsing Base_Stats.c...")
    df = parse_base_stats_file(base_stats_path)
    df = df.with_columns(pl.col("name").map_elements(slugify, return_dtype=pl.String).alias("pokemon_key"))

    parquet_path = curated_dir / "pokemon.parquet"
    df.write_parquet(parquet_path)
    log(f"  -> {parquet_path} ({len(df)} rows)")
    return ("pokemon", parquet_path)


def _parse_level_up_moves(source_dir: Path, curated_dir: Path, log: LogFunc) -> pl.DataFrame | None:
    """Parse Learnsets.c to DataFrame with level-up moves.

    Returns:
        DataFrame with pokemon_key, move_key, learn_method='level', level columns,
        or None if file not found.
    """
    learnsets_path = source_dir / "Learnsets.c"
    if not learnsets_path.exists():
        log(f"Warning: Learnsets.c not found at {learnsets_path}")
        return None

    log("Parsing Learnsets.c (level-up moves)...")
    df = parse_learnsets_file(learnsets_path)
    log(f"  -> {len(df)} level-up move entries")
    return df


def _parse_egg_moves(source_dir: Path, curated_dir: Path, log: LogFunc) -> pl.DataFrame | None:
    """Parse Egg_Moves.c to DataFrame with egg moves.

    Returns:
        DataFrame with pokemon_key, move_key, learn_method='egg', level=None columns,
        or None if file not found.
    """
    egg_moves_path = source_dir / "Egg_Moves.c"
    if not egg_moves_path.exists():
        log(f"Warning: Egg_Moves.c not found at {egg_moves_path}")
        return None

    log("Parsing Egg_Moves.c (egg moves)...")
    df = parse_egg_moves_file(egg_moves_path)
    log(f"  -> {len(df)} egg move entries")
    return df


def _parse_tm_moves(source_dir: Path, curated_dir: Path, log: LogFunc) -> pl.DataFrame | None:
    """Parse tm_compatibility/*.txt to DataFrame with TM moves.

    Returns:
        DataFrame with pokemon_key, move_key, learn_method='tm', level=None columns,
        or None if directory not found.
    """
    tm_dir = source_dir / "tm_compatibility"
    if not tm_dir.exists():
        log(f"Warning: tm_compatibility not found at {tm_dir}")
        return None

    log("Parsing tm_compatibility/*.txt (TM moves)...")
    df = parse_tm_tutor_directory(tm_dir, "tm")
    log(f"  -> {len(df)} TM move entries")
    return df


def _parse_tutor_moves(source_dir: Path, curated_dir: Path, log: LogFunc) -> pl.DataFrame | None:
    """Parse tutor_compatibility/*.txt to DataFrame with tutor moves.

    Returns:
        DataFrame with pokemon_key, move_key, learn_method='tutor', level=None columns,
        or None if directory not found.
    """
    tutor_dir = source_dir / "tutor_compatibility"
    if not tutor_dir.exists():
        log(f"Warning: tutor_compatibility not found at {tutor_dir}")
        return None

    log("Parsing tutor_compatibility/*.txt (tutor moves)...")
    df = parse_tm_tutor_directory(tutor_dir, "tutor")
    log(f"  -> {len(df)} tutor move entries")
    return df


def _combine_pokemon_moves(
    level_up_df: pl.DataFrame | None,
    egg_df: pl.DataFrame | None,
    tm_df: pl.DataFrame | None,
    tutor_df: pl.DataFrame | None,
    curated_dir: Path,
    log: LogFunc,
) -> tuple[str, Path] | None:
    """Combine all move sources into pokemon_moves.parquet.

    Args:
        level_up_df: DataFrame with level-up moves.
        egg_df: DataFrame with egg moves.
        tm_df: DataFrame with TM moves.
        tutor_df: DataFrame with tutor moves.
        curated_dir: Directory for output Parquet files.
        log: Logging callback function.

    Returns:
        Tuple of ('pokemon_moves', parquet_path) or None if all sources are empty.
    """
    dataframes = [df for df in [level_up_df, egg_df, tm_df, tutor_df] if df is not None and len(df) > 0]

    if not dataframes:
        log("Warning: No move data found from any source")
        return None

    log("Combining all move sources...")
    combined_df = pl.concat(dataframes)

    parquet_path = curated_dir / "pokemon_moves.parquet"
    combined_df.write_parquet(parquet_path)
    log(f"  -> {parquet_path} ({len(combined_df)} rows)")

    # Log breakdown by learn_method
    method_counts = combined_df.group_by("learn_method").len().sort("learn_method")
    for row in method_counts.iter_rows():
        log(f"     - {row[0]}: {row[1]} entries")

    return ("pokemon_moves", parquet_path)


def _parse_trainers(
    source_dir: Path,
    curated_dir: Path,
    log: LogFunc,
) -> dict[str, Path]:
    """Parse trainer data into 3 parquet files.

    Args:
        source_dir: Directory containing trainers.txt file.
        curated_dir: Directory for output Parquet files.
        log: Logging callback function.

    Returns:
        Dict with keys: 'trainers', 'trainer_pokemon', 'trainer_pokemon_moves'.
        Empty dict if trainers.txt not found.
    """
    trainers_path = source_dir / "trainers.txt"
    if not trainers_path.exists():
        log(f"Warning: trainers.txt not found at {trainers_path}")
        return {}

    # Import here to avoid circular import
    from unbounddb.ingestion.showdown_parser import parse_showdown_file_to_dataframes  # noqa: PLC0415

    log("Parsing trainers.txt...")
    trainers_df, trainer_pokemon_df, trainer_pokemon_moves_df = parse_showdown_file_to_dataframes(trainers_path)

    results: dict[str, Path] = {}

    # Write trainers
    trainers_parquet = curated_dir / "trainers.parquet"
    trainers_df.write_parquet(trainers_parquet)
    results["trainers"] = trainers_parquet
    log(f"  -> {trainers_parquet} ({len(trainers_df)} rows)")

    # Write trainer_pokemon
    trainer_pokemon_parquet = curated_dir / "trainer_pokemon.parquet"
    trainer_pokemon_df.write_parquet(trainer_pokemon_parquet)
    results["trainer_pokemon"] = trainer_pokemon_parquet
    log(f"  -> {trainer_pokemon_parquet} ({len(trainer_pokemon_df)} rows)")

    # Write trainer_pokemon_moves
    trainer_pokemon_moves_parquet = curated_dir / "trainer_pokemon_moves.parquet"
    trainer_pokemon_moves_df.write_parquet(trainer_pokemon_moves_parquet)
    results["trainer_pokemon_moves"] = trainer_pokemon_moves_parquet
    log(f"  -> {trainer_pokemon_moves_parquet} ({len(trainer_pokemon_moves_df)} rows)")

    return results


def _parse_moves(
    source_dir: Path,
    curated_dir: Path,
    pokemon_moves_df: pl.DataFrame | None,
    log: LogFunc,
) -> tuple[str, Path] | None:
    """Parse moves_info.h to moves parquet, or extract from pokemon_moves as fallback."""
    moves_info_path = source_dir / "moves_info.h"
    if moves_info_path.exists():
        log("Parsing moves_info.h...")
        df = parse_moves_info_file(moves_info_path)
        df = df.with_columns(pl.col("name").map_elements(slugify, return_dtype=pl.String).alias("move_key"))

        parquet_path = curated_dir / "moves.parquet"
        df.write_parquet(parquet_path)
        log(f"  -> {parquet_path} ({len(df)} rows)")
        return ("moves", parquet_path)

    if pokemon_moves_df is not None:
        log("Extracting moves table from pokemon_moves (moves_info.h not found)...")
        moves_df = pokemon_moves_df.select(["move_key"]).unique().sort("move_key")

        parquet_path = curated_dir / "moves.parquet"
        moves_df.write_parquet(parquet_path)
        log(f"  -> {parquet_path} ({len(moves_df)} rows)")
        return ("moves", parquet_path)

    return None


def _parse_evolutions(source_dir: Path, curated_dir: Path, log: LogFunc) -> tuple[str, Path] | None:
    """Parse Evolution Table.c to evolutions parquet."""
    evo_path = source_dir / "Evolution Table.c"
    if not evo_path.exists():
        # Try URL-encoded version
        evo_path = source_dir / "Evolution%20Table.c"
        if not evo_path.exists():
            log(f"Warning: Evolution Table.c not found at {source_dir}")
            return None

    log("Parsing Evolution Table.c...")
    df = parse_evolutions_file(evo_path)

    if len(df) == 0:
        log("  -> No evolutions found (empty result)")
        return None

    parquet_path = curated_dir / "evolutions.parquet"
    df.write_parquet(parquet_path)
    log(f"  -> {parquet_path} ({len(df)} rows)")
    return ("evolutions", parquet_path)


def _parse_locations(source_dir: Path, curated_dir: Path, log: LogFunc) -> tuple[str, Path] | None:
    """Parse locations.csv to locations parquet."""
    locations_path = source_dir / "locations.csv"
    if not locations_path.exists():
        log(f"Warning: locations.csv not found at {locations_path}")
        return None

    log("Parsing locations.csv...")
    df = parse_locations_csv(locations_path)

    if len(df) == 0:
        log("  -> No locations found (empty result)")
        return None

    parquet_path = curated_dir / "locations.parquet"
    df.write_parquet(parquet_path)
    log(f"  -> {parquet_path} ({len(df)} rows)")
    return ("locations", parquet_path)


def run_build_pipeline(
    source_dir: Path | None = None,
    curated_dir: Path | None = None,
    db_path: Path | None = None,
    verbose_callback: Callable[[str], None] | None = None,
) -> Path:
    """Run the full build pipeline: CSV -> Parquet -> DuckDB.

    Args:
        source_dir: Directory containing source CSV files.
        curated_dir: Directory for output Parquet files.
        db_path: Path for the DuckDB database.
        verbose_callback: Optional callback for progress messages.

    Returns:
        Path to the created database.
    """
    if source_dir is None:
        source_dir = settings.raw_exports_dir

    if curated_dir is None:
        curated_dir = settings.curated_dir

    if db_path is None:
        db_path = settings.db_path

    def log(msg: str) -> None:
        if verbose_callback:
            verbose_callback(msg)

    # Get configured tabs
    config = load_sheets_config()
    tab_names = config.get_tab_names()

    # Ensure output directories exist
    curated_dir.mkdir(parents=True, exist_ok=True)

    # Transform CSVs to Parquet
    parquet_files: dict[str, Path] = {}

    for tab_name in tab_names:
        csv_path = source_dir / f"{tab_name}.csv"

        if not csv_path.exists():
            log(f"Skipping {tab_name}: CSV not found at {csv_path}")
            continue

        log(f"Transforming {tab_name}...")

        transformer = get_transformer(tab_name)
        df = transformer(csv_path)

        parquet_path = curated_dir / f"{tab_name}.parquet"
        df.write_parquet(parquet_path)
        parquet_files[tab_name] = parquet_path

        log(f"  -> {parquet_path} ({len(df)} rows)")

    if not parquet_files:
        raise ValueError(f"No CSV files found in {source_dir}")

    # Create database and load Parquet files
    log(f"Creating database at {db_path}...")
    conn = create_database(db_path)

    for table_name, parquet_path in parquet_files.items():
        log(f"Loading {table_name} into database...")
        load_parquet_to_table(conn, parquet_path, table_name)

    # Create indexes
    log("Creating indexes...")
    create_indexes(conn)

    conn.close()
    log(f"Build complete: {db_path}")

    return db_path


def _load_parquets_to_db(parquet_files: dict[str, Path], db_path: Path, log: LogFunc) -> None:
    """Create database and load all parquet files."""
    log(f"Creating database at {db_path}...")
    conn = create_database(db_path)

    for table_name, parquet_path in parquet_files.items():
        log(f"Loading {table_name} into database...")
        load_parquet_to_table(conn, parquet_path, table_name)

    log("Creating indexes...")
    create_indexes(conn)
    conn.close()
    log(f"Build complete: {db_path}")


def run_github_build_pipeline(
    source_dir: Path | None = None,
    curated_dir: Path | None = None,
    db_path: Path | None = None,
    verbose_callback: Callable[[str], None] | None = None,
) -> Path:
    """Run the build pipeline from GitHub C source files.

    Args:
        source_dir: Directory containing source C files.
        curated_dir: Directory for output Parquet files.
        db_path: Path for the DuckDB database.
        verbose_callback: Optional callback for progress messages.

    Returns:
        Path to the created database.
    """
    source_dir = source_dir or settings.raw_github_dir
    curated_dir = curated_dir or settings.curated_dir
    db_path = db_path or settings.db_path

    def log(msg: str) -> None:
        if verbose_callback:
            verbose_callback(msg)

    curated_dir.mkdir(parents=True, exist_ok=True)
    parquet_files: dict[str, Path] = {}

    # Parse source files
    if result := _parse_pokemon(source_dir, curated_dir, log):
        parquet_files[result[0]] = result[1]

    # Parse all move sources
    level_up_df = _parse_level_up_moves(source_dir, curated_dir, log)
    egg_df = _parse_egg_moves(source_dir, curated_dir, log)
    tm_df = _parse_tm_moves(source_dir, curated_dir, log)
    tutor_df = _parse_tutor_moves(source_dir, curated_dir, log)

    # Combine into unified pokemon_moves table
    pokemon_moves_df: pl.DataFrame | None = None
    if result := _combine_pokemon_moves(level_up_df, egg_df, tm_df, tutor_df, curated_dir, log):
        parquet_files[result[0]] = result[1]
        # Read back combined DataFrame for move extraction fallback
        pokemon_moves_df = pl.read_parquet(result[1])

    # Parse moves from moves_info.h or extract from pokemon_moves
    if result := _parse_moves(source_dir, curated_dir, pokemon_moves_df, log):
        parquet_files[result[0]] = result[1]

    # Parse trainer data
    trainer_files = _parse_trainers(source_dir, curated_dir, log)
    parquet_files.update(trainer_files)

    # Parse evolutions
    if result := _parse_evolutions(source_dir, curated_dir, log):
        parquet_files[result[0]] = result[1]

    # Parse locations
    if result := _parse_locations(source_dir, curated_dir, log):
        parquet_files[result[0]] = result[1]

    if not parquet_files:
        raise ValueError(f"No source files found in {source_dir}")

    _load_parquets_to_db(parquet_files, db_path, log)
    return db_path
