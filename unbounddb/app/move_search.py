# ABOUTME: Streamlit UI module for the Advanced Move Search tab.
# ABOUTME: Renders filter panel and grouped result display.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

from unbounddb.app.move_search_filters import MoveSearchFilters
from unbounddb.app.queries import get_available_types, search_moves_advanced

if TYPE_CHECKING:
    from unbounddb.app.location_filters import LocationFilterConfig

# Sort options for results display
_SORT_OPTIONS = {
    "BST (High to Low)": ("bst", True),
    "Attack (High to Low)": ("attack", True),
    "Sp. Attack (High to Low)": ("sp_attack", True),
    "Speed (High to Low)": ("speed", True),
    "Name (A-Z)": ("pokemon_name", False),
}


def _tristate_to_bool(value: str) -> bool | None:
    """Convert a tri-state selectbox value ('Any', 'Yes', 'No') to bool or None."""
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _range_or_none(
    key: str,
    range_min: int,
    range_max: int,
) -> tuple[int | None, int | None]:
    """Extract min/max from a range slider, returning None when at the extremes."""
    low, high = st.session_state.get(key, (range_min, range_max))
    return (low if low > range_min else None, high if high < range_max else None)


def _build_filters_from_widgets(
    filter_config: LocationFilterConfig | None,
    apply_progress: bool,
) -> MoveSearchFilters:
    """Build MoveSearchFilters from current Streamlit session state."""
    from unbounddb.app.queries import get_available_pokemon_set  # noqa: PLC0415
    from unbounddb.app.tm_availability import get_available_tm_move_keys  # noqa: PLC0415

    # Category checkboxes -> tuple
    categories: list[str] = []
    if st.session_state.get("ms_cat_physical"):
        categories.append("Physical")
    if st.session_state.get("ms_cat_special"):
        categories.append("Special")
    if st.session_state.get("ms_cat_status"):
        categories.append("Status")

    # Range sliders -- None when slider spans its full range
    power_min, power_max = _range_or_none("ms_power_range", 0, 300)
    accuracy_min, accuracy_max = _range_or_none("ms_accuracy_range", 0, 100)
    pp_min, pp_max = _range_or_none("ms_pp_range", 0, 64)
    priority_min, priority_max = _range_or_none("ms_priority_range", -7, 5)

    # Stat minimum sliders -- 0 means "no filter"
    min_hp = st.session_state.get("ms_min_hp", 0) or None
    min_attack = st.session_state.get("ms_min_attack", 0) or None
    min_defense = st.session_state.get("ms_min_defense", 0) or None
    min_sp_attack = st.session_state.get("ms_min_sp_attack", 0) or None
    min_sp_defense = st.session_state.get("ms_min_sp_defense", 0) or None
    min_speed = st.session_state.get("ms_min_speed", 0) or None
    min_bst = st.session_state.get("ms_min_bst", 0) or None

    # Max learn level -- 0 means "no filter"
    max_learn_level = st.session_state.get("ms_max_learn_level", 0) or None

    # Game progress
    available_pokemon: frozenset[str] | None = None
    available_tm_keys: frozenset[str] | None = None
    if apply_progress and filter_config is not None:
        available_pokemon = get_available_pokemon_set(filter_config)
        available_tm_keys = get_available_tm_move_keys(filter_config)

    return MoveSearchFilters(
        move_types=tuple(st.session_state.get("ms_move_types", [])),
        categories=tuple(categories),
        power_min=power_min,
        power_max=power_max,
        accuracy_min=accuracy_min,
        accuracy_max=accuracy_max,
        priority_min=priority_min,
        priority_max=priority_max,
        pp_min=pp_min,
        pp_max=pp_max,
        makes_contact=_tristate_to_bool(st.session_state.get("ms_makes_contact", "Any")),
        is_sound_move=_tristate_to_bool(st.session_state.get("ms_is_sound", "Any")),
        is_punch_move=_tristate_to_bool(st.session_state.get("ms_is_punch", "Any")),
        is_bite_move=_tristate_to_bool(st.session_state.get("ms_is_bite", "Any")),
        is_pulse_move=_tristate_to_bool(st.session_state.get("ms_is_pulse", "Any")),
        has_secondary_effect=_tristate_to_bool(st.session_state.get("ms_has_secondary", "Any")),
        learn_methods=tuple(st.session_state.get("ms_learn_methods", [])),
        max_learn_level=max_learn_level,
        stab_only=st.session_state.get("ms_stab_only", False),
        min_hp=min_hp,
        min_attack=min_attack,
        min_defense=min_defense,
        min_sp_attack=min_sp_attack,
        min_sp_defense=min_sp_defense,
        min_speed=min_speed,
        min_bst=min_bst,
        available_pokemon=available_pokemon,
        available_tm_keys=available_tm_keys,
    )


def _render_move_filters() -> None:
    """Render the move filter controls."""
    available_types = get_available_types()
    st.multiselect("Move Type", options=available_types, key="ms_move_types")

    cat_cols = st.columns(3)
    with cat_cols[0]:
        st.checkbox("Physical", key="ms_cat_physical")
    with cat_cols[1]:
        st.checkbox("Special", key="ms_cat_special")
    with cat_cols[2]:
        st.checkbox("Status", key="ms_cat_status")

    st.slider("Power", min_value=0, max_value=300, value=(0, 300), key="ms_power_range")
    st.slider("Accuracy", min_value=0, max_value=100, value=(0, 100), key="ms_accuracy_range")

    range_cols = st.columns(2)
    with range_cols[0]:
        st.slider("PP", min_value=0, max_value=64, value=(0, 64), key="ms_pp_range")
    with range_cols[1]:
        st.slider("Priority", min_value=-7, max_value=5, value=(-7, 5), key="ms_priority_range")

    # Boolean flags
    flag_cols = st.columns(3)
    tristate_opts = ["Any", "Yes", "No"]
    with flag_cols[0]:
        st.selectbox("Makes Contact", tristate_opts, key="ms_makes_contact")
        st.selectbox("Sound Move", tristate_opts, key="ms_is_sound")
    with flag_cols[1]:
        st.selectbox("Punch Move", tristate_opts, key="ms_is_punch")
        st.selectbox("Bite Move", tristate_opts, key="ms_is_bite")
    with flag_cols[2]:
        st.selectbox("Pulse Move", tristate_opts, key="ms_is_pulse")
        st.selectbox("Secondary Effect", tristate_opts, key="ms_has_secondary")


def _render_pokemon_filters() -> None:
    """Render the Pokemon and learn-method filter controls."""
    st.multiselect("Learn Method", options=["level", "egg", "tm", "tutor"], key="ms_learn_methods")

    st.slider("Max Learn Level (0 = no limit)", min_value=0, max_value=100, value=0, key="ms_max_learn_level")

    st.toggle("STAB Only", key="ms_stab_only")

    st.caption("Minimum Stats")
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.slider("HP", min_value=0, max_value=255, value=0, key="ms_min_hp")
        st.slider("Attack", min_value=0, max_value=255, value=0, key="ms_min_attack")
    with stat_cols[1]:
        st.slider("Defense", min_value=0, max_value=255, value=0, key="ms_min_defense")
        st.slider("Sp.Atk", min_value=0, max_value=255, value=0, key="ms_min_sp_attack")
    with stat_cols[2]:
        st.slider("Sp.Def", min_value=0, max_value=255, value=0, key="ms_min_sp_defense")
        st.slider("Speed", min_value=0, max_value=255, value=0, key="ms_min_speed")
    with stat_cols[3]:
        st.slider("BST", min_value=0, max_value=800, value=0, key="ms_min_bst")


def _render_results(results: list[dict[str, Any]], sort_key: str, sort_reverse: bool) -> None:
    """Render search results grouped by Pokemon."""
    # Sort results
    sorted_results = sorted(results, key=lambda r: r.get(sort_key, 0), reverse=sort_reverse)

    # Group by pokemon_key
    unique_pokemon: set[str] = set()
    unique_moves: set[str] = set()
    for r in sorted_results:
        unique_pokemon.add(r["pokemon_key"])
        unique_moves.add(r["move_key"])

    st.write(f"Found **{len(unique_pokemon)}** Pokemon learning **{len(unique_moves)}** matching moves")

    # Group results by pokemon_key preserving sort order
    grouped: list[tuple[str, list[dict[str, Any]]]] = []
    seen: set[str] = set()
    for row in sorted_results:
        pk = row["pokemon_key"]
        if pk not in seen:
            seen.add(pk)
            grouped.append((pk, [r for r in sorted_results if r["pokemon_key"] == pk]))

    for _pokemon_key, rows in grouped:
        first = rows[0]
        type_str = first["pokemon_type1"]
        if first["pokemon_type2"]:
            type_str = f"{first['pokemon_type1']}/{first['pokemon_type2']}"

        abilities = [first["ability1"]]
        if first["ability2"]:
            abilities.append(first["ability2"])
        if first["hidden_ability"]:
            abilities.append(f"{first['hidden_ability']} (H)")
        abilities_str = ", ".join(a for a in abilities if a)

        with st.expander(f"{first['pokemon_name']}  |  {type_str}  |  BST: {first['bst']}"):
            stat_line = (
                f"HP {first['hp']} / ATK {first['attack']} / DEF {first['defense']} / "
                f"SPA {first['sp_attack']} / SPD {first['sp_defense']} / SPE {first['speed']}"
            )
            st.caption(f"{stat_line}  —  {abilities_str}")

            # Build moves table
            moves_table = []
            for row in sorted(rows, key=lambda r: r["power"] or 0, reverse=True):
                stab_str = "Yes" if row["is_stab"] else ""
                learn_str = row["learn_method"]
                if row["level"] and row["level"] > 0:
                    learn_str = f"{row['learn_method']} ({row['level']})"

                moves_table.append(
                    {
                        "Move": row["move_name"],
                        "Type": row["move_type"],
                        "Cat": row["category"],
                        "Power": row["power"] or "-",
                        "Acc": f"{row['accuracy']}%" if row["accuracy"] else "-",
                        "PP": row["pp"] or "-",
                        "STAB": stab_str,
                        "Learn": learn_str,
                    }
                )

            st.dataframe(moves_table, hide_index=True, width="stretch")


def render_move_search_tab(filter_config: LocationFilterConfig | None) -> None:
    """Render the Advanced Move Search tab.

    Args:
        filter_config: Current game progress filter config, or None if no profile active.
    """
    with st.expander("Move Filters", expanded=True):
        _render_move_filters()

    with st.expander("Pokemon Filters"):
        _render_pokemon_filters()

    apply_progress = st.checkbox(
        "Apply Game Progress",
        value=False,
        key="ms_apply_progress",
        disabled=filter_config is None,
        help="Filter by available Pokemon and TMs based on your game progress profile.",
    )

    if st.button("Search", type="primary", key="ms_search_btn"):
        filters = _build_filters_from_widgets(filter_config, apply_progress)
        st.session_state["ms_filters"] = filters

    # Display results if we have a stored filter
    stored_filters = st.session_state.get("ms_filters")
    if stored_filters is not None:
        sort_label = st.selectbox("Sort by", options=list(_SORT_OPTIONS.keys()), key="ms_sort")
        sort_key, sort_reverse = _SORT_OPTIONS[sort_label]

        results = search_moves_advanced(stored_filters)
        if not results:
            st.info("No results found. Try broadening your filters.")
        else:
            _render_results(results, sort_key, sort_reverse)
