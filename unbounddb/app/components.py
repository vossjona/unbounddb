"""ABOUTME: Reusable UI components for displaying Pokemon and move information.
ABOUTME: Provides popover tooltips and clickable elements for navigation."""

from collections.abc import Callable

import streamlit as st

from unbounddb.app.queries import get_move_details, get_pokemon_details
from unbounddb.build.normalize import slugify


def render_move_with_tooltip(move_name: str, move_key: str | None = None) -> None:
    """Render move name with info icon popover showing details.

    Args:
        move_name: Display name of the move.
        move_key: Slugified move key. If None, will be computed from move_name.
    """
    if move_key is None:
        move_key = slugify(move_name)

    cols = st.columns([0.85, 0.15])
    cols[0].write(move_name)

    with cols[1], st.popover(":material/info:", use_container_width=True):
        details = get_move_details(move_key)
        if details:
            st.markdown(f"**{details['name']}**")
            st.markdown(f"**Type:** {details['type']}")
            st.markdown(f"**Category:** {details['category']}")

            # Power/Accuracy/PP row
            power_str = str(details["power"]) if details["power"] else "-"
            acc_str = f"{details['accuracy']}%" if details["accuracy"] else "-"
            pp_str = str(details["pp"]) if details["pp"] else "-"
            st.markdown(f"**Power:** {power_str} | **Acc:** {acc_str} | **PP:** {pp_str}")

            if details["priority"] and details["priority"] != 0:
                st.markdown(f"**Priority:** {details['priority']}")

            if details["effect"]:
                st.markdown("---")
                st.caption(details["effect"])
        else:
            st.write(f"No details found for {move_name}")


def render_pokemon_with_popup(pokemon_name: str, pokemon_key: str | None = None) -> None:
    """Render Pokemon name with info icon popover showing stats and abilities.

    Args:
        pokemon_name: Display name of the Pokemon.
        pokemon_key: Slugified pokemon key. If None, will be computed from pokemon_name.
    """
    if pokemon_key is None:
        pokemon_key = slugify(pokemon_name)

    cols = st.columns([0.75, 0.25])
    cols[0].write(pokemon_name)

    with cols[1], st.popover(":material/info:", use_container_width=True):
        details = get_pokemon_details(pokemon_key)
        if details:
            st.markdown(f"**{details['name']}**")

            # Types
            types_str = details["type1"]
            if details["type2"]:
                types_str = f"{details['type1']} / {details['type2']}"
            st.markdown(f"**Types:** {types_str}")

            st.markdown("---")

            # Stats in a simple table format
            st.markdown(
                f"| Stat | Value |\n"
                f"|------|-------|\n"
                f"| HP | {details['hp']} |\n"
                f"| Attack | {details['attack']} |\n"
                f"| Defense | {details['defense']} |\n"
                f"| Sp.Atk | {details['sp_attack']} |\n"
                f"| Sp.Def | {details['sp_defense']} |\n"
                f"| Speed | {details['speed']} |\n"
                f"| **BST** | **{details['bst']}** |"
            )

            st.markdown("---")

            # Abilities
            abilities: list[str] = []
            if details["ability1"]:
                abilities.append(str(details["ability1"]))
            if details["ability2"]:
                abilities.append(str(details["ability2"]))
            st.markdown(f"**Abilities:** {', '.join(abilities)}")

            if details["hidden_ability"]:
                st.caption(f"Hidden: {details['hidden_ability']}")
        else:
            st.write(f"No details found for {pokemon_name}")


def render_type_badge(
    type_name: str,
    show_pokemon_dialog_callback: Callable[[str, frozenset[str] | None], None] | None = None,
    available_pokemon: frozenset[str] | None = None,
) -> None:
    """Render type as a clickable button that can trigger a Pokemon list dialog.

    Args:
        type_name: The type name to display.
        show_pokemon_dialog_callback: Optional callback function to show Pokemon by type dialog.
            If provided, clicking the type will call this function with type_name.
        available_pokemon: Optional set of available Pokemon for filtering.
    """
    if show_pokemon_dialog_callback is not None:
        if st.button(type_name, key=f"type_badge_{type_name}_{id(available_pokemon)}"):
            show_pokemon_dialog_callback(type_name, available_pokemon)
    else:
        st.write(type_name)
