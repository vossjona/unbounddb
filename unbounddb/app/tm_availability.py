# ABOUTME: TM availability filtering based on game progression.
# ABOUTME: Determines which TM moves are accessible given current locations and HMs.

from pathlib import Path

from unbounddb.app.location_filters import LocationFilterConfig
from unbounddb.app.queries import _get_conn


def get_available_tm_move_keys(
    filter_config: LocationFilterConfig | None,
    db_path: Path | None = None,
) -> set[str] | None:
    """Get the set of TM move keys available at the current game progression.

    Checks each TM against:
    1. Location is in accessible_locations
    2. All required HMs are in available_hms
    3. Post-game TMs only available if post_game is True

    Args:
        filter_config: Current game progress filter config. If None, no
            filtering is applied (all TMs available).
        db_path: Optional path to database.

    Returns:
        Set of move_key strings for available TMs, or None if no filtering
        should be applied (filter_config is None or tm_locations table missing).
    """
    if filter_config is None:
        return None

    conn = _get_conn(db_path)

    # Check if tm_locations table exists
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = {row[0] for row in tables}
    if "tm_locations" not in table_names:
        conn.close()
        return None

    query = "SELECT move_key, location, required_hms, is_post_game FROM tm_locations"
    df = conn.execute(query).pl()
    conn.close()

    if df.is_empty():
        return set()

    accessible = set(filter_config.accessible_locations) if filter_config.accessible_locations else set()
    available_hms = filter_config.available_hms

    available_keys: set[str] = set()

    for row in df.iter_rows(named=True):
        # Check post-game restriction
        if row["is_post_game"] and not filter_config.post_game:
            continue

        # Check location accessibility
        if accessible and row["location"] not in accessible:
            continue

        # Check HM requirements
        required_hms_str: str = row["required_hms"]
        if required_hms_str:
            required = {hm.strip() for hm in required_hms_str.split(",")}
            if not required.issubset(available_hms):
                continue

        available_keys.add(row["move_key"])

    return available_keys
