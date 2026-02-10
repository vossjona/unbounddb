"""ABOUTME: Dialog components for displaying detailed Pokemon information.
ABOUTME: Uses @st.dialog decorator for modal popups with larger content."""

from typing import TYPE_CHECKING

import streamlit as st

from unbounddb.app.location_filters import apply_location_filters
from unbounddb.app.queries import (
    get_pokemon_by_type,
    get_pokemon_learnset,
    search_pokemon_locations,
)
from unbounddb.build.normalize import slugify

if TYPE_CHECKING:
    from unbounddb.app.location_filters import LocationFilterConfig


@st.dialog("Catch Locations", width="large")
def show_locations_dialog(pokemon_name: str, filter_config: "LocationFilterConfig | None") -> None:
    """Show catch locations for a Pokemon in a dialog.

    Args:
        pokemon_name: The Pokemon to find locations for.
        filter_config: Configuration for location filtering based on game progress.
            If None, no filtering is applied.
    """
    st.markdown(f"### Locations for {pokemon_name}")

    locations = search_pokemon_locations(pokemon_name)

    if not locations:
        st.warning(f"No catch locations found for {pokemon_name}.")
        return

    # Apply filters
    filtered = apply_location_filters(locations, filter_config)

    if not filtered:
        st.warning("No locations match the current filters. Try adjusting the Game Progress section.")
        return

    st.caption(f"Found in {len(filtered)} location(s)")

    # Display results table
    table_data = []
    for row in filtered:
        notes = row["encounter_notes"] if row["encounter_notes"] else "-"
        req = row["requirement"] if row["requirement"] else "-"
        table_data.append(
            {
                "Catchable Pokemon": row["pokemon"],
                "Location": row["location_name"],
                "Method": row["encounter_method"],
                "Notes": notes,
                "Requirement": req,
            }
        )

    st.dataframe(table_data, width="stretch", hide_index=True)


@st.dialog("Full Moveset", width="large")
def show_learnset_dialog(pokemon_key: str, pokemon_name: str) -> None:
    """Show complete learnset for a Pokemon in a dialog.

    Args:
        pokemon_key: Slugified pokemon key.
        pokemon_name: Display name of the Pokemon.
    """
    st.markdown(f"### Moveset for {pokemon_name}")

    learnset = get_pokemon_learnset(pokemon_key)

    if not learnset:
        st.warning(f"No moves found for {pokemon_name}.")
        return

    # Add filter controls
    col1, col2 = st.columns(2)

    with col1:
        # Learn method filter
        learn_methods = sorted({r["learn_method"] for r in learnset})
        selected_method = st.selectbox(
            "Filter by Learn Method",
            options=["All", *learn_methods],
            key=f"learnset_method_{pokemon_key}",
        )

    with col2:
        # Category filter
        categories = sorted({r["category"] for r in learnset})
        selected_category = st.selectbox(
            "Filter by Category",
            options=["All", *categories],
            key=f"learnset_category_{pokemon_key}",
        )

    # Apply filters
    filtered = learnset
    if selected_method != "All":
        filtered = [r for r in filtered if r["learn_method"] == selected_method]
    if selected_category != "All":
        filtered = [r for r in filtered if r["category"] == selected_category]

    st.caption(f"Showing {len(filtered)} moves")

    # Display results
    table_data = []
    for row in filtered:
        power_str = str(row["power"]) if row["power"] else "-"
        level_str = str(row["level"]) if row["level"] and row["level"] > 0 else "-"
        table_data.append(
            {
                "Move": row["move_name"],
                "Type": row["move_type"],
                "Category": row["category"],
                "Power": power_str,
                "Learn Method": row["learn_method"],
                "Level": level_str,
            }
        )

    st.dataframe(table_data, width="stretch", hide_index=True)


@st.dialog("Pokemon by Type", width="large")
def show_pokemon_by_type_dialog(type_name: str, available_pokemon: frozenset[str] | None = None) -> None:
    """Show all Pokemon of a specific type in a dialog.

    Args:
        type_name: The type to show Pokemon for.
        available_pokemon: Optional frozenset of Pokemon names to filter by.
    """
    st.markdown(f"### {type_name} Type Pokemon")

    pokemon_list = get_pokemon_by_type(type_name, available_pokemon)

    if not pokemon_list:
        st.warning(f"No Pokemon found with {type_name} type.")
        return

    # Show filter status
    if available_pokemon is not None:
        st.caption(f"Showing {len(pokemon_list)} available Pokemon (filtered by game progress)")
    else:
        st.caption(f"Showing {len(pokemon_list)} Pokemon")

    # Display results
    table_data = []
    for row in pokemon_list:
        types_str = row["type1"]
        if row["type2"]:
            types_str = f"{row['type1']}/{row['type2']}"
        table_data.append(
            {
                "Pokemon": row["name"],
                "Types": types_str,
                "BST": row["bst"],
            }
        )

    st.dataframe(table_data, width="stretch", hide_index=True)


def trigger_locations_dialog(pokemon_name: str, filter_config: "LocationFilterConfig | None") -> None:
    """Wrapper to trigger locations dialog from a button click.

    Args:
        pokemon_name: The Pokemon to find locations for.
        filter_config: Configuration for location filtering. If None, no filtering is applied.
    """
    show_locations_dialog(pokemon_name, filter_config)


def trigger_learnset_dialog(pokemon_name: str) -> None:
    """Wrapper to trigger learnset dialog from a button click.

    Args:
        pokemon_name: Display name of the Pokemon.
    """
    pokemon_key = slugify(pokemon_name)
    show_learnset_dialog(pokemon_key, pokemon_name)


def trigger_type_dialog(type_name: str, available_pokemon: frozenset[str] | None = None) -> None:
    """Wrapper to trigger type dialog from a button click.

    Args:
        type_name: The type to show Pokemon for.
        available_pokemon: Optional frozenset for filtering.
    """
    show_pokemon_by_type_dialog(type_name, available_pokemon)
