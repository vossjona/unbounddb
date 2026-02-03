"""ABOUTME: Streamlit application for Pokemon Unbound queries.
ABOUTME: Provides UI for searching Pokemon by type and move."""

import streamlit as st

from unbounddb.app.queries import (
    get_available_moves,
    get_available_types,
    get_difficulties,
    get_table_list,
    get_table_preview,
    get_trainer_by_id,
    get_trainers_by_difficulty,
    search_pokemon_by_type_and_move,
)
from unbounddb.app.tools.defensive_suggester import (
    analyze_trainer_defense,
    get_neutralized_pokemon_detail,
    get_trainer_move_types,
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

# Load available options
try:
    types = get_available_types()
    moves = get_available_moves()
    tables = get_table_list()
    difficulties = get_difficulties()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Main content area - tabs
tab1, tab2, tab3 = st.tabs(["Search Results", "Browse Tables", "Defensive Type Suggester"])

# Sidebar content changes based on selected tab
# We use session state to track which tab's sidebar to show
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "search"

with tab1:
    st.session_state.active_tab = "search"

with tab2:
    st.session_state.active_tab = "browse"

with tab3:
    st.session_state.active_tab = "defensive"


# Sidebar for search filters (Tab 1)
if st.session_state.active_tab == "search":
    st.sidebar.header("Search Filters")

    # Type selector
    selected_type = st.sidebar.selectbox(
        "Pokemon Type",
        options=["Any", *types],
        index=0,
        key="search_type",
    )

    # Move selector with search
    selected_move = st.sidebar.selectbox(
        "Learns Move",
        options=["Any", *moves],
        index=0,
        key="search_move",
    )

    # Search button
    search_clicked = st.sidebar.button("Search", type="primary", key="search_btn")

# Sidebar for defensive suggester (Tab 3)
elif st.session_state.active_tab == "defensive":
    st.sidebar.header("Trainer Selection")

    # Difficulty dropdown
    selected_difficulty = st.sidebar.selectbox(
        "Difficulty",
        options=["Any", *difficulties],
        index=0,
        key="def_difficulty",
    )

    # Get trainers filtered by difficulty
    difficulty_filter = None if selected_difficulty == "Any" else selected_difficulty
    trainers = get_trainers_by_difficulty(difficulty_filter)

    # Trainer dropdown
    trainer_options = {f"{name} (ID: {tid})": tid for tid, name in trainers}
    selected_trainer_str = st.sidebar.selectbox(
        "Trainer",
        options=list(trainer_options.keys()) if trainer_options else ["No trainers found"],
        index=0,
        key="def_trainer",
    )

    # Analyze button
    analyze_clicked = st.sidebar.button("Analyze Defensive Types", type="primary", key="analyze_btn")

# Tab 1: Search Results
with tab1:
    # Get sidebar values with defaults
    selected_type = st.session_state.get("search_type", "Any")
    selected_move = st.session_state.get("search_move", "Any")
    search_clicked = st.session_state.get("search_btn", False)

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
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Use the sidebar to filter Pokemon by type and/or move, then click Search.")

# Tab 2: Browse Tables
with tab2:
    if tables:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_table = st.selectbox("Select Table", options=tables, key="browse_table")
        with col2:
            show_all = st.checkbox("Show all rows", value=False, key="browse_show_all")

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

# Tab 3: Defensive Type Suggester
with tab3:
    # Get sidebar values
    selected_difficulty = st.session_state.get("def_difficulty", "Any")
    selected_trainer_str = st.session_state.get("def_trainer", "")
    analyze_clicked = st.session_state.get("analyze_btn", False)

    # Parse trainer ID from selection
    difficulty_filter = None if selected_difficulty == "Any" else selected_difficulty
    trainers = get_trainers_by_difficulty(difficulty_filter)
    trainer_options = {f"{name} (ID: {tid})": tid for tid, name in trainers}

    if not trainers:
        st.warning("No trainers found in the database. Please run `unbounddb build` first.")
    elif analyze_clicked and selected_trainer_str in trainer_options:
        trainer_id = trainer_options[selected_trainer_str]
        trainer_info = get_trainer_by_id(trainer_id)

        if trainer_info:
            # Display trainer header
            difficulty_str = f" ({trainer_info['difficulty']})" if trainer_info["difficulty"] else ""
            st.header(f"Trainer: {trainer_info['name']}{difficulty_str}")

            # Get and display move types
            move_types = get_trainer_move_types(trainer_id)
            if move_types:
                st.markdown(f"**Move Types Used:** {', '.join(move_types)} ({len(move_types)} types)")
            else:
                st.warning("No offensive moves found for this trainer's team.")
                st.stop()

            # Analyze defensive types
            analysis_df = analyze_trainer_defense(trainer_id)

            if analysis_df.is_empty():
                st.warning("Could not analyze defensive types.")
            else:
                st.subheader("Best Defensive Typings")

                # Show all checkbox
                show_all_combos = st.checkbox(
                    "Show all 171 combinations",
                    value=False,
                    key="def_show_all",
                )

                # Limit results
                display_df = analysis_df if show_all_combos else analysis_df.head(20)

                # Create display table
                table_data = []
                for row in display_df.iter_rows(named=True):
                    type_combo = row["type1"]
                    if row["type2"]:
                        type_combo = f"{row['type1']}/{row['type2']}"
                    table_data.append(
                        {
                            "Type Combo": type_combo,
                            "Immun": row["immunity_count"],
                            "Resist": row["resistance_count"],
                            "Neutral": row["neutral_count"],
                            "Weak": row["weakness_count"],
                            "Neutralized": f"{row['pokemon_neutralized']}/{len(trainers)}",
                            "Score": row["score"],
                        }
                    )

                st.dataframe(
                    table_data,
                    use_container_width=True,
                    hide_index=True,
                )

                # Expanders for detail view
                st.subheader("Detailed Breakdown")
                for i, row in enumerate(display_df.head(10).iter_rows(named=True)):
                    type_combo = row["type1"]
                    type2 = row["type2"]
                    if type2:
                        type_combo = f"{row['type1']}/{type2}"

                    with st.expander(f"#{i + 1} {type_combo} (Score: {row['score']})"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**Immunities:**")
                            st.write(row["immunities_list"])

                        with col2:
                            st.markdown("**Resistances:**")
                            st.write(row["resistances_list"])

                        with col3:
                            st.markdown("**Weaknesses:**")
                            st.write(row["weaknesses_list"])

                        # Get neutralized Pokemon detail
                        detail_df = get_neutralized_pokemon_detail(trainer_id, row["type1"], type2)

                        if not detail_df.is_empty():
                            neutralized = detail_df.filter(detail_df["is_neutralized"])
                            can_hurt = detail_df.filter(~detail_df["is_neutralized"])

                            total_pokemon = len(detail_df)

                            if not neutralized.is_empty():
                                st.markdown(f"**Pokemon Neutralized ({len(neutralized)}/{total_pokemon}):**")
                                for prow in neutralized.iter_rows(named=True):
                                    eff_str = f"{prow['best_effectiveness']}x"
                                    st.write(
                                        f"- {prow['pokemon_key']} (slot {prow['slot']}): "
                                        f"Best move = {prow['best_move']} ({eff_str})"
                                    )

                            if not can_hurt.is_empty():
                                st.markdown(f"**Can Still Hurt You ({len(can_hurt)}/{total_pokemon}):**")
                                for prow in can_hurt.iter_rows(named=True):
                                    eff_str = f"{prow['best_effectiveness']}x"
                                    st.write(
                                        f"- {prow['pokemon_key']} (slot {prow['slot']}): "
                                        f"{prow['best_move']} ({eff_str})"
                                    )
        else:
            st.error("Could not load trainer information.")
    else:
        st.info(
            "Select a difficulty and trainer from the sidebar, then click 'Analyze Defensive Types' "
            "to find the best defensive type combinations against that trainer's team."
        )
