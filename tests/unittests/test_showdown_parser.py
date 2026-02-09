"""ABOUTME: Tests for Showdown/PokePaste format battle data parsing.
ABOUTME: Verifies TrainerPokemon extraction, EVs parsing, and double battle merging."""

import pytest

from unbounddb.ingestion.showdown_parser import (
    _parse_evs,
    entries_to_dataframes,
    parse_showdown_entry,
    parse_showdown_file,
)


class TestParseEvs:
    """Tests for _parse_evs function."""

    def test_standard_evs(self) -> None:
        """Parse standard EV spread."""
        evs = _parse_evs("252 HP / 252 Def / 4 SpD")
        assert evs["hp"] == 252
        assert evs["defense"] == 252
        assert evs["sp_defense"] == 4
        assert evs["attack"] == 0
        assert evs["sp_attack"] == 0
        assert evs["speed"] == 0

    def test_offensive_evs(self) -> None:
        """Parse offensive EV spread."""
        evs = _parse_evs("252 Atk / 4 Def / 252 Spe")
        assert evs["attack"] == 252
        assert evs["defense"] == 4
        assert evs["speed"] == 252
        assert evs["hp"] == 0

    def test_special_attacker_evs(self) -> None:
        """Parse special attacker EV spread."""
        evs = _parse_evs("252 SpA / 252 Spe / 4 HP")
        assert evs["sp_attack"] == 252
        assert evs["speed"] == 252
        assert evs["hp"] == 4

    def test_mixed_format_evs(self) -> None:
        """Parse EVs with different stat name formats."""
        evs = _parse_evs("252 HP / 128 SpDef / 128 Speed")
        assert evs["hp"] == 252
        assert evs["sp_defense"] == 128
        assert evs["speed"] == 128

    def test_empty_evs(self) -> None:
        """Empty string returns all zeros."""
        evs = _parse_evs("")
        assert all(v == 0 for v in evs.values())


class TestParseShowdownEntry:
    """Tests for parse_showdown_entry function."""

    def test_basic_entry(self) -> None:
        """Parse basic Pokemon entry."""
        lines = [
            "Leader Mirskle - Insane (Floette) @ Grassy Seed",
            "Level: 19",
            "Bold Nature",
            "Ability: Flower Veil",
            "EVs: 252 HP / 252 Def / 4 SpD",
            "- Moonblast",
            "- Petal Blizzard",
            "- Wish",
            "- Grassy Terrain",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.trainer_name == "Leader Mirskle"
        assert entry.difficulty == "Insane"
        assert entry.pokemon == "Floette"
        assert entry.held_item == "Grassy Seed"
        assert entry.level == 19
        assert entry.nature == "Bold"
        assert entry.ability == "Flower Veil"
        assert entry.evs["hp"] == 252
        assert entry.evs["defense"] == 252
        assert entry.evs["sp_defense"] == 4
        assert len(entry.moves) == 4
        assert "Moonblast" in entry.moves

    def test_entry_without_difficulty(self) -> None:
        """Parse entry without difficulty level."""
        lines = [
            "Rival Gary (Bulbasaur) @ Leftovers",
            "Level: 5",
            "Adamant Nature",
            "Ability: Overgrow",
            "EVs: 252 Atk / 252 Spe / 4 HP",
            "- Tackle",
            "- Growl",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.trainer_name == "Rival Gary"
        assert entry.difficulty is None
        assert entry.pokemon == "Bulbasaur"

    def test_entry_without_item(self) -> None:
        """Parse entry without held item."""
        lines = [
            "Trainer Red - Expert (Pikachu)",
            "Level: 50",
            "Timid Nature",
            "Ability: Static",
            "EVs: 252 SpA / 252 Spe / 4 HP",
            "- Thunderbolt",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.held_item is None
        assert entry.pokemon == "Pikachu"

    def test_partner_entry(self) -> None:
        """Parse double battle partner entry."""
        lines = [
            "Shadow Grunt w/ Marlon 1 - Insane (Sableye)",
            "Level: 45",
            "Calm Nature",
            "Ability: Prankster",
            "EVs: 252 HP / 252 Def / 4 SpD",
            "- Will-O-Wisp",
            "- Recover",
            "- Taunt",
            "- Foul Play",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.trainer_name == "Shadow Grunt w/ Marlon 1"
        assert entry.difficulty == "Insane"

    def test_regional_form_pokemon(self) -> None:
        """Parse Pokemon with regional form."""
        lines = [
            "Gym Leader Koga - Insane (Grimer-Alola) @ Eviolite",
            "Level: 40",
            "Bold Nature",
            "Ability: Poison Touch",
            "EVs: 252 HP / 252 Def / 4 SpD",
            "- Minimize",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.pokemon == "Grimer-Alola"

    def test_empty_lines_ignored(self) -> None:
        """Empty lines don't break parsing."""
        lines = [
            "Trainer Red - Expert (Pikachu)",
            "",
            "Level: 50",
            "",
            "Timid Nature",
            "Ability: Static",
            "EVs: 252 SpA / 252 Spe / 4 HP",
            "- Thunderbolt",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is not None
        assert entry.level == 50

    def test_invalid_header_returns_none(self) -> None:
        """Invalid header returns None."""
        lines = [
            "This is not a valid header",
            "Level: 50",
        ]
        entry = parse_showdown_entry(lines)
        assert entry is None


class TestParseShowdownFile:
    """Tests for parse_showdown_file function."""

    def test_multiple_entries(self) -> None:
        """Parse file with multiple trainer entries."""
        content = """Leader Mirskle - Insane (Floette) @ Grassy Seed
Level: 19
Bold Nature
Ability: Flower Veil
EVs: 252 HP / 252 Def / 4 SpD
- Moonblast
- Petal Blizzard
- Wish
- Grassy Terrain

Leader Mirskle - Insane (Whimsicott) @ Focus Sash
Level: 19
Timid Nature
Ability: Prankster
EVs: 252 SpA / 252 Spe / 4 HP
- Moonblast
- Energy Ball
- Tailwind
- Encore"""
        entries = parse_showdown_file(content)
        assert len(entries) == 2
        assert entries[0].pokemon == "Floette"
        assert entries[1].pokemon == "Whimsicott"

    def test_same_trainer_multiple_pokemon(self) -> None:
        """Same trainer with multiple Pokemon entries."""
        content = """Rival Gary (Bulbasaur) @ Leftovers
Level: 5
Adamant Nature
Ability: Overgrow
EVs: 252 Atk / 252 Spe / 4 HP
- Tackle

Rival Gary (Charmander) @ Charcoal
Level: 5
Modest Nature
Ability: Blaze
EVs: 252 SpA / 252 Spe / 4 HP
- Ember"""
        entries = parse_showdown_file(content)
        assert len(entries) == 2
        assert all(e.trainer_name == "Rival Gary" for e in entries)
        assert entries[0].pokemon == "Bulbasaur"
        assert entries[1].pokemon == "Charmander"


class TestEntriesToDataframes:
    """Tests for entries_to_dataframes function."""

    def test_basic_conversion(self) -> None:
        """Convert entries to DataFrames with battle_id column."""
        content = """Leader Mirskle - Insane (Floette) @ Grassy Seed
Level: 19
Bold Nature
Ability: Flower Veil
EVs: 252 HP / 252 Def / 4 SpD
- Moonblast
- Petal Blizzard
- Wish
- Grassy Terrain

Leader Mirskle - Insane (Whimsicott) @ Focus Sash
Level: 19
Timid Nature
Ability: Prankster
EVs: 252 SpA / 252 Spe / 4 HP
- Moonblast
- Energy Ball"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, moves_df = entries_to_dataframes(entries)

        # One unique battle
        assert len(battles_df) == 1
        assert battles_df["name"][0] == "Leader Mirskle"
        assert battles_df["difficulty"][0] == "Insane"
        assert "battle_id" in battles_df.columns

        # Two Pokemon
        assert len(pokemon_df) == 2
        assert pokemon_df["pokemon_key"][0] == "floette"
        assert pokemon_df["pokemon_key"][1] == "whimsicott"
        assert pokemon_df["slot"][0] == 1
        assert pokemon_df["slot"][1] == 2
        assert "battle_id" in pokemon_df.columns

        # 6 moves total (4 + 2)
        assert len(moves_df) == 6
        assert "battle_pokemon_id" in moves_df.columns

    def test_double_battle_merging(self) -> None:
        """Double battle partner Pokemon are merged into main battle entry."""
        content = """Shadow Admin Marlon 1 - Insane (Tyranitar) @ Leftovers
Level: 75
Adamant Nature
Ability: Sand Stream
EVs: 252 HP / 252 Atk / 4 SpD
- Stone Edge

Shadow Admin Marlon 1 - Insane (Garchomp) @ Choice Scarf
Level: 75
Jolly Nature
Ability: Rough Skin
EVs: 252 Atk / 252 Spe / 4 HP
- Earthquake

Shadow Grunt w/ Marlon 1 - Insane (Sableye) @ Sitrus Berry
Level: 70
Calm Nature
Ability: Prankster
EVs: 252 HP / 252 SpD / 4 Def
- Foul Play

Shadow Grunt w/ Marlon 1 - Insane (Muk) @ Black Sludge
Level: 70
Adamant Nature
Ability: Poison Touch
EVs: 252 HP / 252 Atk / 4 SpD
- Gunk Shot"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, _ = entries_to_dataframes(entries)

        # Only one battle entry (partner merged into main)
        assert len(battles_df) == 1
        assert battles_df["name"][0] == "Shadow Admin Marlon 1"

        # All 4 Pokemon belong to the same battle
        assert len(pokemon_df) == 4
        battle_ids = pokemon_df["battle_id"].unique().to_list()
        assert len(battle_ids) == 1

        # Slots are sequential 1-4
        slots = pokemon_df["slot"].to_list()
        assert slots == [1, 2, 3, 4]

    def test_bracket_w_not_treated_as_partner(self) -> None:
        """Entries with w/ inside brackets are standalone, not partners."""
        content = """Crystal Peak [Hoopa w/ Rayquaza] - Insane (Hoopa) @ Focus Sash
Level: 90
Timid Nature
Ability: Magician
EVs: 252 SpA / 252 Spe / 4 HP
- Psychic"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, _ = entries_to_dataframes(entries)

        # Should be a standalone battle (not treated as partner)
        assert len(battles_df) == 1
        assert battles_df["name"][0] == "Crystal Peak [Hoopa w/ Rayquaza]"
        assert len(pokemon_df) == 1

    def test_pokemon_key_slugified(self) -> None:
        """Pokemon names are properly slugified."""
        content = """Trainer Red - Expert (Mr. Mime) @ Choice Specs
Level: 50
Timid Nature
Ability: Filter
EVs: 252 SpA / 252 Spe / 4 HP
- Psychic"""
        entries = parse_showdown_file(content)
        _, pokemon_df, _ = entries_to_dataframes(entries)
        assert pokemon_df["pokemon_key"][0] == "mr_mime"

    def test_move_key_slugified(self) -> None:
        """Move names are properly slugified."""
        content = """Trainer Red - Expert (Pikachu) @ Light Ball
Level: 50
Timid Nature
Ability: Static
EVs: 252 SpA / 252 Spe / 4 HP
- Thunder Wave
- Volt Tackle"""
        entries = parse_showdown_file(content)
        _, _, moves_df = entries_to_dataframes(entries)
        move_keys = moves_df["move_key"].to_list()
        assert "thunder_wave" in move_keys
        assert "volt_tackle" in move_keys

    def test_ev_columns(self) -> None:
        """EV values are correctly stored in columns."""
        content = """Trainer Red - Expert (Pikachu) @ Light Ball
Level: 50
Timid Nature
Ability: Static
EVs: 252 SpA / 252 Spe / 4 HP
- Thunderbolt"""
        entries = parse_showdown_file(content)
        _, pokemon_df, _ = entries_to_dataframes(entries)

        assert pokemon_df["ev_hp"][0] == 4
        assert pokemon_df["ev_attack"][0] == 0
        assert pokemon_df["ev_defense"][0] == 0
        assert pokemon_df["ev_sp_attack"][0] == 252
        assert pokemon_df["ev_sp_defense"][0] == 0
        assert pokemon_df["ev_speed"][0] == 252

    def test_battle_id_assignment(self) -> None:
        """Battle IDs are assigned correctly."""
        content = """Trainer A - Insane (Pikachu)
Level: 50
Timid Nature
Ability: Static
EVs: 4 HP
- Thunderbolt

Trainer B - Expert (Charizard)
Level: 50
Timid Nature
Ability: Blaze
EVs: 4 HP
- Flamethrower

Trainer A - Insane (Raichu)
Level: 50
Timid Nature
Ability: Static
EVs: 4 HP
- Thunder"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, _ = entries_to_dataframes(entries)

        # Two unique battles (Trainer A - Insane and Trainer B - Expert)
        assert len(battles_df) == 2

        # Trainer A has 2 Pokemon, Trainer B has 1
        battle_a_id = battles_df.filter(battles_df["name"] == "Trainer A")["battle_id"][0]
        battle_a_pokemon = pokemon_df.filter(pokemon_df["battle_id"] == battle_a_id)
        assert len(battle_a_pokemon) == 2

    def test_move_slots(self) -> None:
        """Move slots are assigned correctly (1-4)."""
        content = """Trainer Red - Expert (Pikachu) @ Light Ball
Level: 50
Timid Nature
Ability: Static
EVs: 4 HP
- Thunderbolt
- Volt Switch
- Grass Knot
- Hidden Power"""
        entries = parse_showdown_file(content)
        _, _, moves_df = entries_to_dataframes(entries)

        slots = moves_df["slot"].to_list()
        assert slots == [1, 2, 3, 4]

    def test_no_is_double_battle_or_battle_group_columns(self) -> None:
        """Output DataFrames should not have is_double_battle or battle_group columns."""
        content = """Trainer A - Insane (Pikachu)
Level: 50
Timid Nature
Ability: Static
EVs: 4 HP
- Thunderbolt"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, moves_df = entries_to_dataframes(entries)

        assert "is_double_battle" not in battles_df.columns
        assert "battle_group" not in battles_df.columns
        assert "trainer_id" not in battles_df.columns
        assert "trainer_id" not in pokemon_df.columns
        assert "trainer_pokemon_id" not in moves_df.columns

    def test_elite_four_champion_combined(self) -> None:
        """Combined Elite Four + Champion battle is created per difficulty."""
        content = """Elite Four Lorelei - Insane (Lapras) @ Leftovers
Level: 80
Modest Nature
Ability: Water Absorb
EVs: 252 HP / 252 SpA / 4 SpD
- Ice Beam
- Surf

Elite Four Bruno - Insane (Machamp) @ Choice Band
Level: 80
Adamant Nature
Ability: Guts
EVs: 252 Atk / 252 Spe / 4 HP
- Close Combat
- Stone Edge

Champion Gary - Insane (Charizard) @ Charizardite Y
Level: 85
Timid Nature
Ability: Blaze
EVs: 252 SpA / 252 Spe / 4 HP
- Flamethrower
- Air Slash"""
        entries = parse_showdown_file(content)
        battles_df, pokemon_df, _ = entries_to_dataframes(entries)

        # 3 individual battles + 1 combined = 4 total
        assert len(battles_df) == 4

        # Combined battle exists
        combined = battles_df.filter(battles_df["name"] == "Elite Four + Champion")
        assert len(combined) == 1
        assert combined["difficulty"][0] == "Insane"

        # Combined battle has all 3 Pokemon (from 3 individual battles)
        combined_id = combined["battle_id"][0]
        combined_pokemon = pokemon_df.filter(pokemon_df["battle_id"] == combined_id)
        assert len(combined_pokemon) == 3

        # Slots are sequential
        slots = combined_pokemon["slot"].to_list()
        assert slots == [1, 2, 3]

        # Individual battles still exist
        individual = battles_df.filter(battles_df["name"] != "Elite Four + Champion")
        assert len(individual) == 3


class TestDifficultyVariants:
    """Tests for different difficulty levels."""

    @pytest.mark.parametrize(
        "difficulty",
        ["Insane", "Expert", "Difficult", "Easy"],
    )
    def test_all_difficulties_parsed(self, difficulty: str) -> None:
        """All difficulty levels are correctly parsed."""
        content = f"""Trainer Test - {difficulty} (Pikachu)
Level: 50
Timid Nature
Ability: Static
EVs: 4 HP
- Thunderbolt"""
        entries = parse_showdown_file(content)
        assert len(entries) == 1
        assert entries[0].difficulty == difficulty
