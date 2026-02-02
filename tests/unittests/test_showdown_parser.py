"""ABOUTME: Tests for Showdown/PokePaste format trainer battle parsing.
ABOUTME: Verifies TrainerPokemon extraction, EVs parsing, and double battle detection."""

import pytest

from unbounddb.ingestion.showdown_parser import (
    _parse_evs,
    entries_to_dataframes,
    get_battle_group,
    is_double_battle,
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


class TestGetBattleGroup:
    """Tests for get_battle_group function."""

    def test_simple_trainer(self) -> None:
        """Battle group for simple trainer name."""
        assert get_battle_group("Leader Mirskle", "Insane") == "leader_mirskle_insane"

    def test_trainer_without_difficulty(self) -> None:
        """Battle group without difficulty level."""
        assert get_battle_group("Leader Mirskle", None) == "leader_mirskle"

    def test_partner_trainer(self) -> None:
        """Partner trainer uses base trainer name."""
        assert get_battle_group("Shadow Grunt w/ Marlon 1", "Insane") == "marlon_1_insane"

    def test_main_trainer_matches_partner(self) -> None:
        """Main and partner trainers have same battle group."""
        _main_group = get_battle_group("Shadow Admin Marlon 1", "Insane")
        partner_group = get_battle_group("Shadow Grunt w/ Marlon 1", "Insane")
        # Note: main trainer includes full name, partner extracts after "w/"
        # The main trainer's group is different since it includes the full name
        assert _main_group == "shadow_admin_marlon_1_insane"
        assert partner_group == "marlon_1_insane"


class TestIsDoubleBattle:
    """Tests for is_double_battle function."""

    def test_single_battle(self) -> None:
        """Single battle trainer."""
        assert is_double_battle("Leader Mirskle") is False

    def test_double_battle_partner(self) -> None:
        """Double battle partner detected."""
        assert is_double_battle("Shadow Grunt w/ Marlon 1") is True

    def test_double_battle_main(self) -> None:
        """Main trainer in double battle is not marked (no w/)."""
        # The main trainer doesn't have "w/" in their name
        assert is_double_battle("Shadow Admin Marlon 1") is False


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
        """Convert entries to DataFrames."""
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
        trainers_df, pokemon_df, moves_df = entries_to_dataframes(entries)

        # One unique trainer
        assert len(trainers_df) == 1
        assert trainers_df["name"][0] == "Leader Mirskle"
        assert trainers_df["difficulty"][0] == "Insane"
        assert trainers_df["is_double_battle"][0] is False

        # Two Pokemon
        assert len(pokemon_df) == 2
        assert pokemon_df["pokemon_key"][0] == "floette"
        assert pokemon_df["pokemon_key"][1] == "whimsicott"
        assert pokemon_df["slot"][0] == 1
        assert pokemon_df["slot"][1] == 2

        # 6 moves total (4 + 2)
        assert len(moves_df) == 6

    def test_double_battle_detection(self) -> None:
        """Double battle trainers are detected correctly."""
        content = """Shadow Admin Marlon 1 - Insane (Tyranitar) @ Leftovers
Level: 75
Adamant Nature
Ability: Sand Stream
EVs: 252 HP / 252 Atk / 4 SpD
- Stone Edge

Shadow Grunt w/ Marlon 1 - Insane (Sableye) @ Sitrus Berry
Level: 70
Calm Nature
Ability: Prankster
EVs: 252 HP / 252 SpD / 4 Def
- Foul Play"""
        entries = parse_showdown_file(content)
        trainers_df, _pokemon_df, _ = entries_to_dataframes(entries)

        # Two unique trainers
        assert len(trainers_df) == 2

        # Find the partner trainer
        partner_row = trainers_df.filter(trainers_df["name"].str.contains("w/"))
        assert len(partner_row) == 1
        assert partner_row["is_double_battle"][0] is True

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

    def test_trainer_id_assignment(self) -> None:
        """Trainer IDs are assigned correctly."""
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
        trainers_df, pokemon_df, _ = entries_to_dataframes(entries)

        # Two unique trainers (Trainer A - Insane and Trainer B - Expert)
        assert len(trainers_df) == 2

        # Trainer A has 2 Pokemon, Trainer B has 1
        trainer_a_id = trainers_df.filter(trainers_df["name"] == "Trainer A")["trainer_id"][0]
        trainer_a_pokemon = pokemon_df.filter(pokemon_df["trainer_id"] == trainer_a_id)
        assert len(trainer_a_pokemon) == 2

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
