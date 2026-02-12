# ABOUTME: Frozen dataclass defining all filter parameters for Advanced Move Search.
# ABOUTME: Hashable for Streamlit cache compatibility.

from dataclasses import dataclass


@dataclass(frozen=True)
class MoveSearchFilters:
    """Filter parameters for the Advanced Move Search query."""

    # Move filters
    move_names: tuple[str, ...] = ()
    move_types: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    power_min: int | None = None
    power_max: int | None = None
    accuracy_min: int | None = None
    accuracy_max: int | None = None
    priority_min: int | None = None
    priority_max: int | None = None
    pp_min: int | None = None
    pp_max: int | None = None
    makes_contact: bool | None = None
    is_sound_move: bool | None = None
    is_punch_move: bool | None = None
    is_bite_move: bool | None = None
    is_pulse_move: bool | None = None
    has_secondary_effect: bool | None = None

    # Pokemon/learn filters
    learn_methods: tuple[str, ...] = ()
    max_learn_level: int | None = None
    stab_only: bool = False
    min_hp: int | None = None
    min_attack: int | None = None
    min_defense: int | None = None
    min_sp_attack: int | None = None
    min_sp_defense: int | None = None
    min_speed: int | None = None
    min_bst: int | None = None

    # Game progress filters (populated from get_available_pokemon_set / get_available_tm_move_keys)
    available_pokemon: frozenset[str] | None = None  # Pokemon NAMES (not keys)
    available_tm_keys: frozenset[str] | None = None  # Move keys
