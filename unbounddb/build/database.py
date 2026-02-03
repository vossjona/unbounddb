"""ABOUTME: DuckDB database operations for loading and querying data.
ABOUTME: Handles Parquet loading and index creation."""

from pathlib import Path

import duckdb


def create_database(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Create or connect to a DuckDB database.

    Args:
        db_path: Path to the database file.

    Returns:
        DuckDB connection.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database to start fresh
    if db_path.exists():
        db_path.unlink()

    return duckdb.connect(str(db_path))


def load_parquet_to_table(
    conn: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    table_name: str,
) -> None:
    """Load a Parquet file into a DuckDB table.

    Args:
        conn: DuckDB connection.
        parquet_path: Path to the Parquet file.
        table_name: Name for the table in the database.
    """
    # table_name comes from internal code, not user input
    conn.execute(
        f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet(?)",  # noqa: S608
        [str(parquet_path)],
    )


def create_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    """Create indexes on key columns for efficient joining.

    Args:
        conn: DuckDB connection with loaded tables.
    """
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    # Index pokemon_key and move_key columns for efficient joins
    # table_name comes from schema introspection, not user input
    for table_name in table_names:
        columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
        col_names = [c[0] for c in columns]

        if "pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_pokemon_key ON {table_name}(pokemon_key)")

        if "move_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_move_key ON {table_name}(move_key)")

        # Index for trainer foreign keys
        if "trainer_id" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_trainer_id ON {table_name}(trainer_id)")

        if "trainer_pokemon_id" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_trainer_pokemon_id ON {table_name}(trainer_pokemon_id)")

        # Index for evolution foreign keys
        if "from_pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_from_pokemon_key ON {table_name}(from_pokemon_key)")

        if "to_pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_to_pokemon_key ON {table_name}(to_pokemon_key)")

        # Index for location name
        if "location_name" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_location_name ON {table_name}(location_name)")


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Get a read-only connection to an existing database.

    Args:
        db_path: Path to the database file.

    Returns:
        DuckDB connection.

    Raises:
        FileNotFoundError: If database doesn't exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    return duckdb.connect(str(db_path), read_only=True)
