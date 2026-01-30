"""ABOUTME: Per-table transformers for CSV to Parquet conversion.
ABOUTME: Uses flexible column discovery to handle varying sheet structures."""

from collections.abc import Callable
from pathlib import Path

import polars as pl

from unbounddb.build.normalize import slugify

TransformerFunc = Callable[[Path], pl.DataFrame]


def _find_name_column(df: pl.DataFrame, candidates: list[str]) -> str | None:
    """Find a name column from a list of candidates (case-insensitive).

    Args:
        df: DataFrame to search.
        candidates: List of possible column names.

    Returns:
        The actual column name if found, None otherwise.
    """
    lower_to_actual = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_to_actual:
            return lower_to_actual[candidate.lower()]
    return None


def _add_key_column(
    df: pl.DataFrame,
    source_col: str,
    key_col: str,
) -> pl.DataFrame:
    """Add a slugified key column based on a source column.

    Args:
        df: Input DataFrame.
        source_col: Column to derive the key from.
        key_col: Name for the new key column.

    Returns:
        DataFrame with added key column.
    """
    return df.with_columns(pl.col(source_col).map_elements(slugify, return_dtype=pl.String).alias(key_col))


def transform_pokemon(csv_path: Path) -> pl.DataFrame:
    """Transform pokemon CSV to normalized DataFrame.

    Discovers the name column and adds pokemon_key for joining.
    Preserves all original columns.

    Args:
        csv_path: Path to the raw CSV file.

    Returns:
        Transformed DataFrame with pokemon_key column.
    """
    df = pl.read_csv(csv_path, infer_schema_length=10000)

    name_candidates = ["name", "pokemon", "pokemon_name", "species"]
    name_col = _find_name_column(df, name_candidates)

    if name_col is None:
        raise ValueError(
            f"Could not find name column in pokemon CSV. Columns: {df.columns}, Candidates: {name_candidates}"
        )

    df = _add_key_column(df, name_col, "pokemon_key")

    return df


def transform_moves(csv_path: Path) -> pl.DataFrame:
    """Transform moves CSV to normalized DataFrame.

    Discovers the name column and adds move_key for joining.
    Preserves all original columns.

    Args:
        csv_path: Path to the raw CSV file.

    Returns:
        Transformed DataFrame with move_key column.
    """
    df = pl.read_csv(csv_path, infer_schema_length=10000)

    name_candidates = ["name", "move", "move_name"]
    name_col = _find_name_column(df, name_candidates)

    if name_col is None:
        raise ValueError(
            f"Could not find name column in moves CSV. Columns: {df.columns}, Candidates: {name_candidates}"
        )

    df = _add_key_column(df, name_col, "move_key")

    return df


def transform_learnsets(csv_path: Path) -> pl.DataFrame:
    """Transform learnsets CSV to normalized DataFrame.

    Discovers pokemon and move name columns and adds keys for joining.
    Preserves all original columns.

    Args:
        csv_path: Path to the raw CSV file.

    Returns:
        Transformed DataFrame with pokemon_key and move_key columns.
    """
    df = pl.read_csv(csv_path, infer_schema_length=10000)

    pokemon_candidates = ["pokemon", "pokemon_name", "species", "name"]
    pokemon_col = _find_name_column(df, pokemon_candidates)

    if pokemon_col is None:
        raise ValueError(
            f"Could not find pokemon column in learnsets CSV. Columns: {df.columns}, Candidates: {pokemon_candidates}"
        )

    move_candidates = ["move", "move_name", "attack"]
    move_col = _find_name_column(df, move_candidates)

    if move_col is None:
        raise ValueError(
            f"Could not find move column in learnsets CSV. Columns: {df.columns}, Candidates: {move_candidates}"
        )

    df = _add_key_column(df, pokemon_col, "pokemon_key")
    df = _add_key_column(df, move_col, "move_key")

    return df


def transform_generic(csv_path: Path) -> pl.DataFrame:
    """Generic transformer for unknown table types.

    Simply reads the CSV without adding any key columns.

    Args:
        csv_path: Path to the raw CSV file.

    Returns:
        DataFrame with original columns.
    """
    return pl.read_csv(csv_path, infer_schema_length=10000)


TRANSFORMERS: dict[str, TransformerFunc] = {
    "pokemon": transform_pokemon,
    "moves": transform_moves,
    "learnsets": transform_learnsets,
}


def get_transformer(table_name: str) -> TransformerFunc:
    """Get the appropriate transformer for a table.

    Args:
        table_name: Name of the table.

    Returns:
        Transformer function for the table.
    """
    return TRANSFORMERS.get(table_name, transform_generic)
