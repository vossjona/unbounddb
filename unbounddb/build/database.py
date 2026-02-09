# ABOUTME: SQLite database operations for loading and querying data.
# ABOUTME: Handles Parquet loading, index creation, and query result conversion.

import sqlite3
from pathlib import Path

import polars as pl


def create_database(db_path: Path) -> sqlite3.Connection:
    """Create or connect to a SQLite database.

    Args:
        db_path: Path to the database file.

    Returns:
        SQLite connection.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database to start fresh
    if db_path.exists():
        db_path.unlink()

    return sqlite3.connect(str(db_path))


def load_parquet_to_table(
    conn: sqlite3.Connection,
    parquet_path: Path,
    table_name: str,
) -> None:
    """Load a Parquet file into a SQLite table.

    Reads the Parquet file with Polars, then writes to SQLite via pandas bridge.

    Args:
        conn: SQLite connection.
        parquet_path: Path to the Parquet file.
        table_name: Name for the table in the database.
    """
    df = pl.read_parquet(parquet_path)
    df.to_pandas().to_sql(table_name, conn, if_exists="replace", index=False)
    conn.commit()


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes on key columns for efficient joining.

    Args:
        conn: SQLite connection with loaded tables.
    """
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]

    # Index pokemon_key and move_key columns for efficient joins
    # table_name comes from schema introspection, not user input
    for table_name in table_names:
        columns = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        col_names = [c[1] for c in columns]

        if "pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_pokemon_key ON {table_name}(pokemon_key)")

        if "move_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_move_key ON {table_name}(move_key)")

        # Index for battle foreign keys
        if "battle_id" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_battle_id ON {table_name}(battle_id)")

        if "battle_pokemon_id" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_battle_pokemon_id ON {table_name}(battle_pokemon_id)")

        # Index for evolution foreign keys
        if "from_pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_from_pokemon_key ON {table_name}(from_pokemon_key)")

        if "to_pokemon_key" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_to_pokemon_key ON {table_name}(to_pokemon_key)")

        # Index for location name
        if "location_name" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_location_name ON {table_name}(location_name)")

        # Index for pokemon_moves learn_method
        if "learn_method" in col_names:
            conn.execute(f"CREATE INDEX idx_{table_name}_learn_method ON {table_name}(learn_method)")

    conn.commit()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a connection to an existing database.

    Args:
        db_path: Path to the database file.

    Returns:
        SQLite connection.

    Raises:
        FileNotFoundError: If database doesn't exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    return sqlite3.connect(str(db_path))


def fetchall_to_polars(cursor: sqlite3.Cursor) -> pl.DataFrame:
    """Convert a SQLite cursor result to a Polars DataFrame.

    Args:
        cursor: Executed SQLite cursor with results.

    Returns:
        Polars DataFrame with query results.
    """
    if cursor.description is None:
        return pl.DataFrame()

    column_names = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    if not rows:
        return pl.DataFrame({col: [] for col in column_names})

    return pl.DataFrame(rows, schema=column_names, orient="row")
