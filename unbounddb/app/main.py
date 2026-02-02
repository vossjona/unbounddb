"""ABOUTME: Streamlit application for Pokemon Unbound queries.
ABOUTME: Provides UI for searching Pokemon by type and move."""

import streamlit as st

from unbounddb.app.queries import (
    get_available_moves,
    get_available_types,
    get_table_list,
    get_table_preview,
    search_pokemon_by_type_and_move,
)
from unbounddb.settings import settings

st.set_page_config(
    page_title="Pokemon Unbound DB",
    page_icon=":pokemon:",
    layout="wide",
)

st.title("Pokemon Unbound Database")

# Check if database exists
if not settings.db_path.exists():
    st.error(f"Database not found at `{settings.db_path}`. Please run `unbounddb fetch` and `unbounddb build` first.")
    st.stop()

# Sidebar for search filters
st.sidebar.header("Search Filters")

# Load available options
try:
    types = get_available_types()
    moves = get_available_moves()
    tables = get_table_list()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Type selector
selected_type = st.sidebar.selectbox(
    "Pokemon Type",
    options=["Any", *types],
    index=0,
)

# Move selector with search
selected_move = st.sidebar.selectbox(
    "Learns Move",
    options=["Any", *moves],
    index=0,
)

# Search button
search_clicked = st.sidebar.button("Search", type="primary", width="stretch")

# Main content area
tab1, tab2 = st.tabs(["Search Results", "Browse Tables"])

with tab1:
    if search_clicked or (selected_type != "Any" or selected_move != "Any"):
        type_filter = selected_type if selected_type != "Any" else None
        move_filter = selected_move if selected_move != "Any" else None

        if type_filter is None and move_filter is None:
            st.info("Select a type or move to search, or click Search to view all Pokemon.")
            results = search_pokemon_by_type_and_move()
        else:
            results = search_pokemon_by_type_and_move(
                pokemon_type=type_filter,
                move_name=move_filter,
            )

        st.subheader(f"Results ({len(results)} Pokemon)")

        if len(results) == 0:
            st.warning("No Pokemon found matching the criteria.")
        else:
            st.dataframe(
                results.to_pandas(),
                width="stretch",
                hide_index=True,
            )
    else:
        st.info("Use the sidebar to filter Pokemon by type and/or move, then click Search.")

with tab2:
    if tables:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_table = st.selectbox("Select Table", options=tables)
        with col2:
            show_all = st.checkbox("Show all rows", value=False)

        if selected_table:
            limit = None if show_all else 100
            preview = get_table_preview(selected_table, limit=limit)
            row_label = "all" if show_all else f"{len(preview)} of"
            st.subheader(f"{selected_table} ({row_label} {len(preview)} rows)")
            st.dataframe(
                preview.to_pandas(),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.warning("No tables found in database.")
