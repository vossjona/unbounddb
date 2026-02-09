"""ABOUTME: Streamlit application for Pokemon Unbound queries.
ABOUTME: Provides UI for browsing tables, battle matchups, and Pokemon locations."""

import streamlit as st

from unbounddb.app.components import (
    render_pokemon_with_popup,
)
from unbounddb.app.dialogs import (
    show_learnset_dialog,
    show_locations_dialog,
)
from unbounddb.app.game_progress_persistence import (
    create_new_profile,
    delete_profile_by_name,
    get_active_profile_name,
    get_all_profile_names,
    load_profile,
    save_profile_progress,
    set_active_profile,
)
from unbounddb.app.location_filters import LocationFilterConfig, apply_location_filters
from unbounddb.app.queries import (
    get_all_pokemon_names_from_locations,
    get_available_pokemon_set,
    get_battle_by_id,
    get_battles_by_difficulty,
    get_difficulties,
    get_first_blocked_evolution,
    get_move_details,
    get_table_list,
    get_table_preview,
    search_pokemon_locations,
)
from unbounddb.app.tm_availability import get_available_tm_move_keys
from unbounddb.app.tools.defensive_suggester import (
    analyze_battle_defense,
    get_battle_move_types,
    get_neutralized_pokemon_detail,
)
from unbounddb.app.tools.offensive_suggester import (
    analyze_four_type_coverage,
    analyze_single_type_offense,
    get_battle_pokemon_types,
    get_single_type_detail,
    get_type_coverage_detail,
)
from unbounddb.app.tools.phys_spec_analyzer import (
    analyze_battle_defensive_profile,
    analyze_battle_offensive_profile,
)
from unbounddb.app.tools.pokemon_ranker import (
    get_coverage_detail,
    get_pokemon_moves_detail,
    get_recommended_types,
    rank_pokemon_for_battle,
)
from unbounddb.app.user_database import update_profile as _db_update_profile
from unbounddb.progression.progression_data import (
    compute_filter_config,
    get_dropdown_labels,
    load_progression,
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
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Rod level options for index lookup
ROD_LEVEL_OPTIONS = ["Super Rod", "Good Rod", "Old Rod", "None"]

# Load progression data (cached)
_progression_entries = load_progression()
_progression_labels = get_dropdown_labels(_progression_entries)

# Profile selector options: dynamic from database + "None (ignore filters)"
profile_names = get_all_profile_names()
PROFILE_OPTIONS = [*profile_names, "None (ignore filters)"]


def _on_profile_change() -> None:
    """Callback when profile selector changes."""
    selected = st.session_state.get("profile_selector")
    if selected == "None (ignore filters)":
        set_active_profile(None)
        # Clear widget keys when switching to "None" profile
        keys_to_clear = [
            "global_progression_step",
            "global_rod",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    else:
        profile_name: str = str(selected)
        set_active_profile(profile_name)
        # Load the new profile's values and update session state
        _, saved_difficulty, step, rod = load_profile(profile_name)
        st.session_state["global_progression_step"] = step
        st.session_state["global_rod"] = rod
        st.session_state["def_difficulty"] = saved_difficulty if saved_difficulty else "Any"


def _save_current_progress() -> None:
    """Callback to save current game progress settings to the active profile."""
    active_profile = get_active_profile_name()
    if active_profile is None:
        return  # Don't save when "None" profile is selected

    progression_step = st.session_state.get("global_progression_step", 0)
    rod_level = st.session_state.get("global_rod", "None")
    difficulty = st.session_state.get("def_difficulty")
    difficulty_to_save = difficulty if difficulty != "Any" else None
    save_profile_progress(active_profile, progression_step, rod_level, difficulty=difficulty_to_save)


def _save_difficulty() -> None:
    """Callback to save difficulty selection to current profile."""
    active_profile = get_active_profile_name()
    if active_profile is None:
        return

    difficulty = st.session_state.get("def_difficulty")
    difficulty_to_save = difficulty if difficulty != "Any" else None
    _db_update_profile(active_profile, difficulty=difficulty_to_save)


# Get active profile name
active_profile_name = get_active_profile_name()

# Determine initial index for profile selector
if active_profile_name is None:
    profile_index = PROFILE_OPTIONS.index("None (ignore filters)")
else:
    profile_index = PROFILE_OPTIONS.index(active_profile_name) if active_profile_name in PROFILE_OPTIONS else 0

# Profile selector
selected_profile = st.selectbox(
    "Profile",
    options=PROFILE_OPTIONS,
    index=profile_index,
    key="profile_selector",
    on_change=_on_profile_change,
    help="Select a game progress profile or 'None' to show all Pokemon without filtering",
)

# Manage Profiles expander
with st.expander("Manage Profiles", expanded=False):
    new_name = st.text_input("New profile name", key="new_profile_input")
    if st.button("Create Profile", key="create_profile_btn"):
        if new_name and new_name.strip():
            if create_new_profile(new_name.strip()):
                st.success(f"Created profile '{new_name}'")
                st.rerun()
            else:
                st.error(f"Profile '{new_name}' already exists")
        else:
            st.warning("Please enter a profile name")

    # Delete button (only if a real profile is selected)
    if (
        selected_profile != "None (ignore filters)"
        and st.button(f"Delete '{selected_profile}'", key="delete_profile_btn", type="secondary")
        and delete_profile_by_name(selected_profile)
    ):
        st.rerun()

# Determine if filtering is active
filtering_active = selected_profile != "None (ignore filters)"

# Load saved profile data for initializing session state
saved_config: LocationFilterConfig | None = None
saved_difficulty: str | None = None
saved_step: int = 0
saved_rod: str = "None"

if filtering_active:
    saved_config, saved_difficulty, saved_step, saved_rod = load_profile(selected_profile)

# Initialize session state from saved profile on first load (when keys don't exist)
if filtering_active:
    if "global_progression_step" not in st.session_state:
        st.session_state["global_progression_step"] = saved_step
    if "global_rod" not in st.session_state:
        st.session_state["global_rod"] = saved_rod
    if "def_difficulty" not in st.session_state and saved_difficulty:
        st.session_state["def_difficulty"] = saved_difficulty

# Global Game Progress Config (collapsible, hidden when profile is None)
if filtering_active:
    with st.expander("Game Progress", expanded=False):
        st.caption("Select the last trainer you defeated to auto-configure location and move filters.")

        st.selectbox(
            "Last Defeated Trainer",
            options=range(len(_progression_labels)),
            format_func=lambda i: _progression_labels[i],
            key="global_progression_step",
            on_change=_save_current_progress,
        )

        st.selectbox(
            "Rod Level",
            options=ROD_LEVEL_OPTIONS,
            key="global_rod",
            on_change=_save_current_progress,
        )

    # Build global filter config from progression data
    step = st.session_state.get("global_progression_step", 0)
    difficulty_for_config = st.session_state.get("def_difficulty")
    if difficulty_for_config == "Any":
        difficulty_for_config = None
    rod_level = st.session_state.get("global_rod", "None")
    global_filter_config: LocationFilterConfig | None = compute_filter_config(
        _progression_entries, step, difficulty_for_config, rod_level
    )
else:
    # No filtering when profile is None
    global_filter_config = None

# Main content area - 3 tabs with inline controls
tab1, tab2, tab3 = st.tabs(["Browse", "Battle Matchups", "Pokemon Locations"])

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

# Tab 2: Battle Matchups (Defensive + Offensive)
with tab2:
    # Battle selection at top of tab
    battle_col1, battle_col2, battle_col3 = st.columns([2, 3, 1])

    with battle_col1:
        # Get saved difficulty index for default selection
        difficulty_options = ["Any", *difficulties]
        default_difficulty_index = 0
        if "def_difficulty" in st.session_state:
            saved_diff = st.session_state["def_difficulty"]
            if saved_diff in difficulty_options:
                default_difficulty_index = difficulty_options.index(saved_diff)

        selected_difficulty = st.selectbox(
            "Difficulty",
            options=difficulty_options,
            index=default_difficulty_index,
            key="def_difficulty",
            on_change=_save_difficulty,
        )

    # Get battles filtered by difficulty
    difficulty_filter = None if selected_difficulty == "Any" else selected_difficulty
    battles = get_battles_by_difficulty(difficulty_filter)
    battle_options = {f"{name} (ID: {bid})": bid for bid, name in battles}

    with battle_col2:
        selected_battle_str = st.selectbox(
            "Battle",
            options=list(battle_options.keys()) if battle_options else ["No battles found"],
            index=0,
            key="def_battle",
        )

    with battle_col3:
        st.write("")  # Spacer to align button with selectboxes
        analyze_clicked = st.button("Analyze", type="primary", key="analyze_btn")

    st.divider()

    # Store analyzed battle in session state so it persists across checkbox reruns
    if analyze_clicked and selected_battle_str in battle_options:
        st.session_state["analyzed_battle_id"] = battle_options[selected_battle_str]

    # Check if we have an analyzed battle (either from this click or previous)
    analyzed_battle_id = st.session_state.get("analyzed_battle_id")

    if not battles:
        st.warning("No battles found in the database. Please run `unbounddb build` first.")
    elif analyzed_battle_id is not None:
        battle_id = analyzed_battle_id
        battle_info = get_battle_by_id(battle_id)

        if battle_info:
            # Display battle header
            difficulty_str = f" ({battle_info['difficulty']})" if battle_info["difficulty"] else ""
            st.header(f"Battle: {battle_info['name']}{difficulty_str}")

            # Get battle's team info
            pokemon_types = get_battle_pokemon_types(battle_id)
            team_names = [p["pokemon_key"] for p in pokemon_types]
            if team_names:
                st.markdown(f"**Team:** {', '.join(team_names)}")

            # Nested tabs for defensive/offensive/physical-special analysis and Pokemon ranker
            def_tab, off_tab, phys_spec_tab, ranker_tab = st.tabs(
                ["Defensive Analysis", "Offensive Analysis", "Physical/Special", "Pokemon Ranker"]
            )

            # --- DEFENSIVE ANALYSIS TAB ---
            with def_tab:
                # Get and display move types
                move_types = get_battle_move_types(battle_id)
                if move_types:
                    st.markdown(f"**Move Types Used:** {', '.join(move_types)} ({len(move_types)} types)")
                else:
                    st.warning("No offensive moves found for this battle's team.")
                    st.stop()

                # Analyze defensive types
                analysis_df = analyze_battle_defense(battle_id)

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
                            detail_df = get_neutralized_pokemon_detail(battle_id, row["type1"], type2)

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
                    st.warning("No Pokemon found for this battle's team.")
                else:
                    # --- Individual Type Rankings ---
                    st.subheader("Individual Type Rankings")

                    single_type_df = analyze_single_type_offense(battle_id)

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
                                detail_df = get_single_type_detail(battle_id, atk_type)

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

                    coverage_df = analyze_four_type_coverage(battle_id)

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
                                detail_df = get_type_coverage_detail(battle_id, types_list)

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
                    st.warning("No Pokemon found for this battle's team.")
                else:
                    # Section 1: Their Offensive Profile
                    st.subheader("Their Offensive Profile")
                    st.caption("What type of moves does the battle use? Should you prioritize Defense or Sp.Def?")

                    offensive_profile = analyze_battle_offensive_profile(battle_id)

                    if offensive_profile["recommendation"] == "No data available":
                        st.warning("No move data available for this battle's team.")
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
                        "What defensive stats does the battle's team have? Should you use Physical or Special moves?"
                    )

                    defensive_profile = analyze_battle_defensive_profile(battle_id)

                    if defensive_profile["recommendation"] == "No data available":
                        st.warning("No stat data available for this battle's team.")
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
                    st.warning("No Pokemon found for this battle's team.")
                else:
                    st.subheader("Recommended Pokemon")
                    st.caption(
                        "Best Pokemon to use against this battle, ranked by defensive typing, "
                        "offensive moves, and stat alignment."
                    )

                    # Get analysis summary
                    recommended_type_list = get_recommended_types(battle_id)
                    defensive_profile_ranker = analyze_battle_defensive_profile(battle_id)
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

                    # Get available Pokemon and TMs based on game progress
                    available_pokemon = get_available_pokemon_set(global_filter_config)
                    available_tm_keys = get_available_tm_move_keys(global_filter_config)

                    # Get rankings - filter by available Pokemon and TMs
                    limit = 0 if show_all_pokemon else 50
                    rankings_df = rank_pokemon_for_battle(
                        battle_id,
                        top_n=limit,
                        available_pokemon=available_pokemon,
                        available_tm_keys=available_tm_keys,
                    )

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
                                # Quick action buttons
                                btn_col1, btn_col2, btn_col3 = st.columns([0.3, 0.35, 0.35])
                                with btn_col1:
                                    render_pokemon_with_popup(row["name"], row["pokemon_key"])
                                with btn_col2:
                                    if st.button(
                                        ":material/location_on: Locations",
                                        key=f"loc_btn_{row['pokemon_key']}",
                                    ):
                                        show_locations_dialog(row["name"], global_filter_config)
                                with btn_col3:
                                    if st.button(
                                        ":material/list: Full Moveset",
                                        key=f"moveset_btn_{row['pokemon_key']}",
                                    ):
                                        show_learnset_dialog(row["pokemon_key"], row["name"])

                                st.divider()

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
                                coverage_detail = get_coverage_detail(
                                    row["pokemon_key"], battle_id, available_tm_keys=available_tm_keys
                                )
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
                                good_moves = get_pokemon_moves_detail(
                                    row["pokemon_key"], battle_id, available_tm_keys=available_tm_keys
                                )
                                if good_moves:
                                    st.markdown("**Recommended Moves:**")

                                    # Display moves table with full details
                                    moves_table = []
                                    for move in good_moves:  # Show all diversified moves (max 15)
                                        stab_str = "Yes" if move["is_stab"] else "No"
                                        learn_str = move["learn_method"]
                                        if move["level"] and move["level"] > 0:
                                            learn_str = f"{move['learn_method']} ({move['level']})"

                                        # Get additional move details (accuracy, PP)
                                        move_details = get_move_details(move["move_key"])
                                        acc_str = (
                                            f"{move_details['accuracy']}%"
                                            if move_details and move_details["accuracy"]
                                            else "-"
                                        )
                                        pp_str = str(move_details["pp"]) if move_details and move_details["pp"] else "-"

                                        moves_table.append(
                                            {
                                                "Move": move["move_name"],
                                                "Type": move["move_type"],
                                                "Cat": move["category"],
                                                "Pow": move["power"] or "-",
                                                "Acc": acc_str,
                                                "PP": pp_str,
                                                "STAB": stab_str,
                                                "Learn": learn_str,
                                            }
                                        )
                                    st.dataframe(moves_table, hide_index=True, width="stretch")
                                else:
                                    st.write("No recommended moves found for this Pokemon.")

        else:
            st.error("Could not load battle information.")
    else:
        st.info(
            "Select a difficulty and battle above, then click 'Analyze' "
            "to find the best defensive and offensive type combinations against that battle's team."
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

        # Pokemon info popup for the searched Pokemon
        render_pokemon_with_popup(f":material/info: View {selected_pokemon} Stats", selected_pokemon)

        # Query locations for selected Pokemon
        locations_df = search_pokemon_locations(selected_pokemon)

        if locations_df.is_empty():
            st.warning(f"No catch locations found for {selected_pokemon}.")
        else:
            # Apply global filters
            filtered_df = apply_location_filters(locations_df, global_filter_config)

            if filtered_df.is_empty():
                unfiltered_pokemon = set(locations_df["pokemon"].unique().to_list())
                if selected_pokemon not in unfiltered_pokemon:
                    # Evolved form — pre-evos exist in DB but none pass filters
                    pre_evo_names = ", ".join(sorted(unfiltered_pokemon))
                    st.warning(
                        f"{selected_pokemon} can only be obtained by evolving "
                        f"{pre_evo_names}, which is not available in your "
                        f"currently accessible locations."
                    )
                else:
                    st.warning(
                        f"{selected_pokemon} is not available in your currently "
                        f"accessible locations. Try adjusting the Game Progress "
                        f"section at the top of the page."
                    )
            else:
                # Show level cap warning if the searched Pokemon isn't directly catchable
                catchable_names = set(filtered_df["pokemon"].unique().to_list())
                if (
                    selected_pokemon not in catchable_names
                    and global_filter_config is not None
                    and global_filter_config.level_cap is not None
                ):
                    block = get_first_blocked_evolution(selected_pokemon, global_filter_config.level_cap)
                    if block:
                        st.warning(
                            f"{block['from_pokemon']} evolves into "
                            f"{block['to_pokemon']} at Level {block['level']}, "
                            f"but your level cap is "
                            f"{global_filter_config.level_cap}."
                        )

                st.subheader(f"Found in {len(filtered_df)} location(s)")

                # Show info popups for unique catchable Pokemon (pre-evolutions)
                unique_pokemon = filtered_df["pokemon"].unique().to_list()
                if len(unique_pokemon) > 1:
                    st.caption("Click to view stats for catchable forms:")
                    pokemon_cols = st.columns(min(len(unique_pokemon), 4))
                    for i, pkmn in enumerate(unique_pokemon):
                        with pokemon_cols[i % 4]:
                            render_pokemon_with_popup(pkmn)

                st.divider()

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

                st.dataframe(table_data, width="stretch", hide_index=True)
