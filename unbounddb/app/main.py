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
from unbounddb.app.tools.offensive_suggester import (
    analyze_four_type_coverage,
    analyze_single_type_offense,
    get_single_type_detail,
    get_trainer_pokemon_types,
    get_type_coverage_detail,
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
tab1, tab2, tab3 = st.tabs(["Search Results", "Browse Tables", "Type Suggester"])

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
    analyze_clicked = st.sidebar.button("Analyze Types", type="primary", key="analyze_btn")

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
                width="stretch",
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
                width="stretch",
                hide_index=True,
            )
    else:
        st.warning("No tables found in database.")

# Tab 3: Type Suggester (Defensive + Offensive)
with tab3:
    # Get sidebar values
    selected_difficulty = st.session_state.get("def_difficulty", "Any")
    selected_trainer_str = st.session_state.get("def_trainer", "")
    analyze_clicked = st.session_state.get("analyze_btn", False)

    # Parse trainer ID from selection
    difficulty_filter = None if selected_difficulty == "Any" else selected_difficulty
    trainers = get_trainers_by_difficulty(difficulty_filter)
    trainer_options = {f"{name} (ID: {tid})": tid for tid, name in trainers}

    # Store analyzed trainer in session state so it persists across checkbox reruns
    if analyze_clicked and selected_trainer_str in trainer_options:
        st.session_state["analyzed_trainer_id"] = trainer_options[selected_trainer_str]

    # Check if we have an analyzed trainer (either from this click or previous)
    analyzed_trainer_id = st.session_state.get("analyzed_trainer_id")

    if not trainers:
        st.warning("No trainers found in the database. Please run `unbounddb build` first.")
    elif analyzed_trainer_id is not None:
        trainer_id = analyzed_trainer_id
        trainer_info = get_trainer_by_id(trainer_id)

        if trainer_info:
            # Display trainer header
            difficulty_str = f" ({trainer_info['difficulty']})" if trainer_info["difficulty"] else ""
            st.header(f"Trainer: {trainer_info['name']}{difficulty_str}")

            # Get trainer's team info
            pokemon_types = get_trainer_pokemon_types(trainer_id)
            team_names = [p["pokemon_key"] for p in pokemon_types]
            if team_names:
                st.markdown(f"**Trainer's Team:** {', '.join(team_names)}")

            # Nested tabs for defensive/offensive analysis
            def_tab, off_tab = st.tabs(["Defensive Analysis", "Offensive Analysis"])

            # --- DEFENSIVE ANALYSIS TAB ---
            with def_tab:
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
                                "Neutralized": f"{row['pokemon_neutralized']}/{len(pokemon_types)}",
                                "Score": row["score"],
                            }
                        )

                    st.dataframe(
                        table_data,
                        width="stretch",
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

            # --- OFFENSIVE ANALYSIS TAB ---
            with off_tab:
                if not pokemon_types:
                    st.warning("No Pokemon found for this trainer's team.")
                else:
                    # --- Individual Type Rankings ---
                    st.subheader("Individual Type Rankings")

                    single_type_df = analyze_single_type_offense(trainer_id)

                    if single_type_df.is_empty():
                        st.warning("Could not analyze offensive types.")
                    else:
                        show_all_types = st.checkbox(
                            "Show all 18 types",
                            value=False,
                            key="off_show_all_types",
                        )

                        display_single_df = single_type_df if show_all_types else single_type_df.head(10)

                        # Create display table
                        single_table_data = [
                            {
                                "Type": row["type"],
                                "4x": row["4x_count"],
                                "2x": row["2x_count"],
                                "Neutral": row["neutral_count"],
                                "Resist": row["resisted_count"],
                                "Immune": row["immune_count"],
                                "Score": row["score"],
                            }
                            for row in display_single_df.iter_rows(named=True)
                        ]

                        st.dataframe(
                            single_table_data,
                            width="stretch",
                            hide_index=True,
                        )

                        # Expanders for individual type details
                        for row in display_single_df.head(5).iter_rows(named=True):
                            atk_type = row["type"]
                            with st.expander(f"{atk_type} Details (Score: {row['score']})"):
                                detail_df = get_single_type_detail(trainer_id, atk_type)

                                if not detail_df.is_empty():
                                    for prow in detail_df.iter_rows(named=True):
                                        type_str = prow["type1"]
                                        if prow["type2"]:
                                            type_str = f"{prow['type1']}/{prow['type2']}"
                                        eff_str = f"{prow['effectiveness']}x"
                                        category = prow["category"]
                                        st.write(f"- {prow['pokemon_key']} ({type_str}): {eff_str} ({category})")

                    # --- 4-Type Coverage ---
                    st.subheader("Best 4-Type Coverage")
                    st.caption("Pokemon can learn 4 moves. These combinations maximize super-effective coverage.")

                    coverage_df = analyze_four_type_coverage(trainer_id)

                    if coverage_df.is_empty():
                        st.warning("Could not analyze type coverage.")
                    else:
                        show_all_combos_off = st.checkbox(
                            "Show all combinations",
                            value=False,
                            key="off_show_all_combos",
                        )

                        display_coverage_df = coverage_df if show_all_combos_off else coverage_df.head(20)

                        # Create display table
                        coverage_table_data = [
                            {
                                "Types": row["types"],
                                "Covered": f"{row['covered_count']}/{row['total_pokemon']}",
                                "Coverage": f"{row['coverage_pct']}%",
                                "Score": row["score"],
                            }
                            for row in display_coverage_df.iter_rows(named=True)
                        ]

                        st.dataframe(
                            coverage_table_data,
                            width="stretch",
                            hide_index=True,
                        )

                        # Expanders for coverage details
                        for row in display_coverage_df.head(5).iter_rows(named=True):
                            types_str = row["types"]
                            types_list = [t.strip() for t in types_str.split(",")]

                            with st.expander(f"{types_str} (Score: {row['score']})"):
                                detail_df = get_type_coverage_detail(trainer_id, types_list)

                                if not detail_df.is_empty():
                                    covered = detail_df.filter(detail_df["is_covered"])
                                    not_covered = detail_df.filter(~detail_df["is_covered"])

                                    if not covered.is_empty():
                                        st.markdown("**Covered (2x+):**")
                                        for prow in covered.iter_rows(named=True):
                                            type_str = prow["type1"]
                                            if prow["type2"]:
                                                type_str = f"{prow['type1']}/{prow['type2']}"
                                            st.write(
                                                f"- {prow['pokemon_key']} ({type_str}): "
                                                f"{prow['best_type']} ({prow['best_effectiveness']}x)"
                                            )

                                    if not not_covered.is_empty():
                                        st.markdown("**Not Covered (<2x):**")
                                        for prow in not_covered.iter_rows(named=True):
                                            type_str = prow["type1"]
                                            if prow["type2"]:
                                                type_str = f"{prow['type1']}/{prow['type2']}"
                                            best_info = (
                                                f"{prow['best_type']} ({prow['best_effectiveness']}x)"
                                                if prow["best_type"]
                                                else "No effective type"
                                            )
                                            st.write(f"- {prow['pokemon_key']} ({type_str}): {best_info}")
        else:
            st.error("Could not load trainer information.")
    else:
        st.info(
            "Select a difficulty and trainer from the sidebar, then click 'Analyze Types' "
            "to find the best defensive and offensive type combinations against that trainer's team."
        )
