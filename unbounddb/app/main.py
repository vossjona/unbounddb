"""ABOUTME: Streamlit application for Pokemon Unbound queries.
ABOUTME: Provides UI for browsing tables, trainer matchups, and Pokemon locations."""

import streamlit as st

from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters
from unbounddb.app.queries import (
    get_all_location_names,
    get_all_pokemon_names_from_locations,
    get_available_pokemon_set,
    get_difficulties,
    get_table_list,
    get_table_preview,
    get_trainer_by_id,
    get_trainers_by_difficulty,
    search_pokemon_locations,
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
from unbounddb.app.tools.phys_spec_analyzer import (
    analyze_trainer_defensive_profile,
    analyze_trainer_offensive_profile,
)
from unbounddb.app.tools.pokemon_ranker import (
    get_coverage_detail,
    get_pokemon_moves_detail,
    get_recommended_types,
    rank_pokemon_for_trainer,
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
    tables = get_table_list()
    difficulties = get_difficulties()
    all_locations = get_all_location_names()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Global Game Progress Config (collapsible, before tabs)
with st.expander("Game Progress", expanded=False):
    st.caption("Configure your current game progress to filter available Pokemon in the Ranker and Locations tabs.")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        global_has_surf = st.checkbox("Surf", value=True, key="global_surf")
        global_has_dive = st.checkbox("Dive", value=True, key="global_dive")
    with col2:
        global_has_rock_smash = st.checkbox("Rock Smash", value=True, key="global_rock_smash")
        global_post_game = st.checkbox("Post Game", value=True, key="global_post_game")
    with col3:
        global_rod_level = st.selectbox(
            "Rod Level",
            options=["Super Rod", "Good Rod", "Old Rod", "None"],
            index=0,
            key="global_rod",
        )
    with col4:
        global_level_cap = st.number_input(
            "Level Cap",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            key="global_level_cap",
            help="Set to 0 for no limit. Filters Pokemon that evolve above this level.",
        )
    with col5:
        global_accessible_locations = st.multiselect(
            "Accessible Locations",
            options=all_locations,
            default=[],
            key="global_accessible",
            help="Leave empty to show all locations",
        )

# Build global filter config
global_filter_config = LocationFilterConfig(
    has_surf=global_has_surf,
    has_dive=global_has_dive,
    rod_level=global_rod_level,
    has_rock_smash=global_has_rock_smash,
    post_game=global_post_game,
    accessible_locations=global_accessible_locations if global_accessible_locations else None,
    level_cap=global_level_cap if global_level_cap > 0 else None,
)

# Main content area - 3 tabs with inline controls
tab1, tab2, tab3 = st.tabs(["Browse", "Trainer Matchups", "Pokemon Locations"])

# Tab 1: Browse Tables
with tab1:
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

# Tab 2: Trainer Matchups (Defensive + Offensive)
with tab2:
    # Trainer selection at top of tab
    trainer_col1, trainer_col2, trainer_col3 = st.columns([2, 3, 1])

    with trainer_col1:
        selected_difficulty = st.selectbox(
            "Difficulty",
            options=["Any", *difficulties],
            index=0,
            key="def_difficulty",
        )

    # Get trainers filtered by difficulty
    difficulty_filter = None if selected_difficulty == "Any" else selected_difficulty
    trainers = get_trainers_by_difficulty(difficulty_filter)
    trainer_options = {f"{name} (ID: {tid})": tid for tid, name in trainers}

    with trainer_col2:
        selected_trainer_str = st.selectbox(
            "Trainer",
            options=list(trainer_options.keys()) if trainer_options else ["No trainers found"],
            index=0,
            key="def_trainer",
        )

    with trainer_col3:
        st.write("")  # Spacer to align button with selectboxes
        analyze_clicked = st.button("Analyze", type="primary", key="analyze_btn")

    st.divider()

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

            # Nested tabs for defensive/offensive/physical-special analysis and Pokemon ranker
            def_tab, off_tab, phys_spec_tab, ranker_tab = st.tabs(
                ["Defensive Analysis", "Offensive Analysis", "Physical/Special", "Pokemon Ranker"]
            )

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

            # --- PHYSICAL/SPECIAL ANALYSIS TAB ---
            with phys_spec_tab:
                if not pokemon_types:
                    st.warning("No Pokemon found for this trainer's team.")
                else:
                    # Section 1: Their Offensive Profile
                    st.subheader("Their Offensive Profile")
                    st.caption("What type of moves does the trainer use? Should you prioritize Defense or Sp.Def?")

                    offensive_profile = analyze_trainer_offensive_profile(trainer_id)

                    if offensive_profile["recommendation"] == "No data available":
                        st.warning("No move data available for this trainer's team.")
                    else:
                        # Bar chart: Physical vs Special attacker counts
                        attacker_data = {
                            "Type": ["Physical", "Special", "Mixed"],
                            "Count": [
                                offensive_profile["physical_count"],
                                offensive_profile["special_count"],
                                offensive_profile["mixed_count"],
                            ],
                        }
                        st.bar_chart(attacker_data, x="Type", y="Count", horizontal=True)

                        # Team stats
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Avg Team Attack", offensive_profile["avg_team_attack"])
                            st.metric("Total Physical Power", offensive_profile["total_physical_power"])
                        with col2:
                            st.metric("Avg Team Sp.Attack", offensive_profile["avg_team_sp_attack"])
                            st.metric("Total Special Power", offensive_profile["total_special_power"])

                        # Recommendation
                        st.info(f"**Recommendation:** {offensive_profile['recommendation']}")

                        # Per-Pokemon breakdown
                        with st.expander("Per-Pokemon Breakdown"):
                            for pdetail in offensive_profile["pokemon_details"]:
                                pokemon_key = pdetail["pokemon_key"]
                                profile = pdetail["profile"]
                                attack = pdetail["attack"]
                                sp_attack = pdetail["sp_attack"]
                                phys_moves = pdetail["physical_moves"]
                                spec_moves = pdetail["special_moves"]

                                move_info = []
                                if phys_moves:
                                    move_info.append(f"Physical: {', '.join(phys_moves)}")
                                if spec_moves:
                                    move_info.append(f"Special: {', '.join(spec_moves)}")
                                move_str = " | ".join(move_info) if move_info else "No offensive moves"

                                st.write(
                                    f"- **{pokemon_key}** (Atk: {attack}, SpA: {sp_attack}): {profile} - {move_str}"
                                )

                    st.divider()

                    # Section 2: Our Offensive Strategy
                    st.subheader("Your Offensive Strategy")
                    st.caption(
                        "What defensive stats does the trainer's team have? Should you use Physical or Special moves?"
                    )

                    defensive_profile = analyze_trainer_defensive_profile(trainer_id)

                    if defensive_profile["recommendation"] == "No data available":
                        st.warning("No stat data available for this trainer's team.")
                    else:
                        # Bar chart: Defensive profile counts
                        defender_data = {
                            "Type": ["Physically Defensive", "Specially Defensive", "Balanced"],
                            "Count": [
                                defensive_profile["physically_defensive_count"],
                                defensive_profile["specially_defensive_count"],
                                defensive_profile["balanced_count"],
                            ],
                        }
                        st.bar_chart(defender_data, x="Type", y="Count", horizontal=True)

                        # Team stats
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Avg Team Defense", defensive_profile["avg_team_defense"])
                        with col2:
                            st.metric("Avg Team Sp.Defense", defensive_profile["avg_team_sp_defense"])

                        # Recommendation
                        st.info(f"**Recommendation:** {defensive_profile['recommendation']}")

                        # Per-Pokemon breakdown
                        with st.expander("Per-Pokemon Breakdown"):
                            for pdetail in defensive_profile["pokemon_details"]:
                                pokemon_key = pdetail["pokemon_key"]
                                profile = pdetail["profile"]
                                defense = pdetail["defense"]
                                sp_defense = pdetail["sp_defense"]

                                st.write(f"- **{pokemon_key}** (Def: {defense}, SpD: {sp_defense}): {profile}")

            # --- POKEMON RANKER TAB ---
            with ranker_tab:
                if not pokemon_types:
                    st.warning("No Pokemon found for this trainer's team.")
                else:
                    st.subheader("Recommended Pokemon")
                    st.caption(
                        "Best Pokemon to use against this trainer, ranked by defensive typing, "
                        "offensive moves, and stat alignment."
                    )

                    # Get analysis summary
                    recommended_type_list = get_recommended_types(trainer_id)
                    defensive_profile_ranker = analyze_trainer_defensive_profile(trainer_id)
                    phys_spec_rec = defensive_profile_ranker.get("recommendation", "Either works")

                    # Display analysis summary
                    if recommended_type_list:
                        top_types_str = ", ".join([rt["type"] for rt in recommended_type_list])
                        st.markdown(f"**Top Attack Types:** {top_types_str}")
                    st.markdown(f"**Stat Focus:** {phys_spec_rec}")

                    st.divider()

                    # Show all checkbox
                    show_all_pokemon = st.checkbox(
                        "Show all Pokemon (default: top 50)",
                        value=False,
                        key="ranker_show_all",
                    )

                    # Get available Pokemon based on game progress
                    available_pokemon = get_available_pokemon_set(global_filter_config)

                    # Get rankings - filter by available Pokemon
                    limit = 0 if show_all_pokemon else 50
                    rankings_df = rank_pokemon_for_trainer(trainer_id, top_n=limit, available_pokemon=available_pokemon)

                    if rankings_df.is_empty():
                        st.warning("Could not rank Pokemon. Make sure move data is available.")
                    else:
                        # Create display table
                        ranker_table_data = []
                        for row in rankings_df.iter_rows(named=True):
                            type_combo = row["type1"]
                            if row["type2"]:
                                type_combo = f"{row['type1']}/{row['type2']}"
                            ranker_table_data.append(
                                {
                                    "Rank": row["rank"],
                                    "Pokemon": row["name"],
                                    "Types": type_combo,
                                    "BST": row["bst"],
                                    "Score": row["total_score"],
                                    "Covers": row["covers"],
                                    "Top Moves": row["top_moves"],
                                }
                            )

                        st.dataframe(
                            ranker_table_data,
                            width="stretch",
                            hide_index=True,
                        )

                        # Expanders for top Pokemon details
                        st.subheader("Detailed Breakdown")
                        for row in rankings_df.head(10).iter_rows(named=True):
                            type_combo = row["type1"]
                            if row["type2"]:
                                type_combo = f"{row['type1']}/{row['type2']}"

                            with st.expander(
                                f"#{row['rank']} {row['name']} ({type_combo}) - Score: {row['total_score']}"
                            ):
                                # Score breakdown
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Defense Score", row["defense_score"])
                                with col2:
                                    st.metric("Offense Score", row["offense_score"])
                                with col3:
                                    st.metric("Stat Score", row["stat_score"])
                                with col4:
                                    st.metric("BST Score", row["bst_score"])

                                # Defensive typing info
                                st.markdown("**Defensive Typing:**")
                                def_col1, def_col2, def_col3 = st.columns(3)
                                with def_col1:
                                    st.write(f"Immunities: {row['immunities']}")
                                with def_col2:
                                    st.write(f"Resistances: {row['resistances']}")
                                with def_col3:
                                    st.write(f"Weaknesses: {row['weaknesses']}")

                                # Coverage breakdown
                                coverage_detail = get_coverage_detail(row["pokemon_key"], trainer_id)
                                if coverage_detail:
                                    covered_count = sum(1 for c in coverage_detail if c["is_covered"])
                                    total_count = len(coverage_detail)
                                    st.markdown(f"**Coverage:** {covered_count}/{total_count}")

                                    for cov in coverage_detail:
                                        type_str = cov["type1"]
                                        if cov["type2"]:
                                            type_str = f"{cov['type1']}/{cov['type2']}"
                                        if cov["is_covered"]:
                                            eff_str = f"{cov['effectiveness']}x"
                                            st.write(
                                                f"- ✓ {cov['pokemon_key']} ({type_str}) - "
                                                f"{cov['best_move_type']} ({eff_str})"
                                            )
                                        else:
                                            st.write(f"- ✗ {cov['pokemon_key']} ({type_str})")

                                # Recommended moves detail
                                good_moves = get_pokemon_moves_detail(row["pokemon_key"], trainer_id)
                                if good_moves:
                                    st.markdown("**Recommended Moves:**")
                                    moves_table = []
                                    for move in good_moves[:8]:  # Show top 8 moves
                                        stab_str = "Yes" if move["is_stab"] else "No"
                                        learn_str = move["learn_method"]
                                        if move["level"] and move["level"] > 0:
                                            learn_str = f"{move['learn_method']} ({move['level']})"
                                        moves_table.append(
                                            {
                                                "Move": move["move_name"],
                                                "Type": move["move_type"],
                                                "Power": move["power"],
                                                "Category": move["category"],
                                                "STAB": stab_str,
                                                "Learn": learn_str,
                                            }
                                        )
                                    st.dataframe(moves_table, hide_index=True, width="stretch")
                                else:
                                    st.write("No recommended moves found for this Pokemon.")

        else:
            st.error("Could not load trainer information.")
    else:
        st.info(
            "Select a difficulty and trainer above, then click 'Analyze' "
            "to find the best defensive and offensive type combinations against that trainer's team."
        )

# Tab 3: Pokemon Locations
with tab3:
    # Get available Pokemon for search
    location_pokemon = get_all_pokemon_names_from_locations()

    # Pokemon search selectbox
    selected_pokemon = st.selectbox(
        "Pokemon",
        options=["Select a Pokemon...", *location_pokemon],
        index=0,
        key="loc_pokemon_search",
    )

    st.divider()

    # Results section
    if selected_pokemon == "Select a Pokemon...":
        st.info(
            "Select a Pokemon above to see where it can be caught. "
            "Use the Game Progress section above to filter by your current progress."
        )
    else:
        st.header(f"Catch Locations for {selected_pokemon}")

        # Query locations for selected Pokemon
        locations_df = search_pokemon_locations(selected_pokemon)

        if locations_df.is_empty():
            st.warning(f"No catch locations found for {selected_pokemon}.")
        else:
            # Apply global filters
            filtered_df = apply_location_filters(locations_df, global_filter_config)

            if filtered_df.is_empty():
                st.warning(
                    "No locations match the current filters. "
                    "Try adjusting the Game Progress section at the top of the page."
                )
            else:
                st.subheader(f"Found in {len(filtered_df)} location(s)")

                # Display results table
                table_data = []
                for row in filtered_df.iter_rows(named=True):
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

                st.dataframe(
                    table_data,
                    width="stretch",
                    hide_index=True,
                )
