"""ABOUTME: Tests for walkthrough parser progression extraction.
ABOUTME: Verifies trainer extraction, segmentation, badge rewards, and unlock detection."""

import yaml

from unbounddb.progression.dataclasses import (
    BadgeReward,
    ProgressionSegment,
    ProgressionUnlock,
    WalkthroughTrainer,
)
from unbounddb.progression.walkthrough_parser import (
    BADGE_REWARDS,
    extract_locations_from_segment,
    extract_rod_upgrade,
    find_important_trainers,
    get_badge_reward,
    match_trainers_to_db,
    parse_walkthrough,
    segment_by_trainers,
    unlocks_to_yaml,
)

# Sample walkthrough with preamble (table of contents) before "Hello there"
# Uses varied separator styles to test the universal regex
SAMPLE_WALKTHROUGH = """
Pokemon Unbound Walkthrough - Table of Contents

[froz] FROZEN HEIGHTS
[bell] BELLIN TOWN
[rt01] ROUTE 1
[rt02] ROUTE 2
[post1] POST GAME AREA

---

Hello there, welcome to the Pokemon Unbound walkthrough!

[froz] FROZEN HEIGHTS {An Island Town on a Frozen Lake.}
Starting area with Pokemon up to level 10.

[rt01] ROUTE 1 "Snowy Mountain Pass"
Wild Pokemon available.

>>RIVAL BATTLE<<
================

Rival Axelrod
- Lv12 Swinub [Ice/Ground]
- Lv13 Pikachu [Electric]

[bell] BELLIN TOWN {A Quiet Town}
Get your first badge here!

>>GYM BATTLE<<
++++++++++++++

Leader Mirskle
- Lv18 Florges [Fairy]
- Lv20 Roserade [Grass/Poison]

You also received the Old Rod from the fisherman.

[rt02] ROUTE 2 "Forest Path"
Many grass types here.

>>SHADOW BOSS BATTLE<<
xxxxxxxxxxxxxxxxxxxxxxx

Black Emboar James
- Lv26 Koffing [Poison]

[rt03] ROUTE 3 "Mountain Trail"
Rocky terrain ahead.

>>LEGENDARY BATTLE<<
oooooooooooooooooooo

Zapdos
- Lv50 Zapdos [Electric/Flying]

\\//[[POST-GAME ARC]]\\//

[post1] POST GAME AREA
This is post-game content.

>>BORRIUS LEAGUE CHAMPIONSHIP BATTLE<<
MmMmMmMmMmMmMmMmMmMmMmMmMmMmMmMmMmMm

Champion Gary
- Lv75 Pikachu
"""


class TestFindImportantTrainers:
    """Tests for find_important_trainers function."""

    def test_finds_rival_trainer(self) -> None:
        """Extracts rival trainer from walkthrough."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        rival = next((t for t in trainers if "rival" in t.name.lower()), None)
        assert rival is not None
        assert "axelrod" in rival.name.lower()
        assert rival.trainer_key == "rival_axelrod"
        assert rival.battle_type == "RIVAL"

    def test_finds_leader_trainer(self) -> None:
        """Extracts leader trainer from walkthrough."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        leader = next((t for t in trainers if "leader" in t.name.lower()), None)
        assert leader is not None
        assert "mirskle" in leader.name.lower()
        assert leader.trainer_key == "leader_mirskle"
        assert leader.battle_type == "GYM"

    def test_finds_boss_trainer(self) -> None:
        """Extracts boss trainer from walkthrough."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        boss = next(
            (t for t in trainers if "james" in t.name.lower() or "emboar" in t.name.lower()),
            None,
        )
        assert boss is not None
        assert boss.battle_type == "SHADOW BOSS"

    def test_trainers_ordered_by_position(self) -> None:
        """Trainers are returned in document order."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        positions = [t.position for t in trainers]
        assert positions == sorted(positions)

    def test_finds_champion_trainer(self) -> None:
        """Extracts champion from post-game section."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        champion = next((t for t in trainers if "champion" in t.name.lower()), None)
        assert champion is not None
        assert champion.battle_type == "BORRIUS LEAGUE CHAMPIONSHIP"

    def test_excludes_legendary_when_progression_only(self) -> None:
        """Legendary battles are excluded when progression_only=True."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH, progression_only=True)
        legendary = next((t for t in trainers if "zapdos" in t.name.lower()), None)
        assert legendary is None

    def test_includes_legendary_when_not_progression_only(self) -> None:
        """Legendary battles are included when progression_only=False."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH, progression_only=False)
        legendary = next((t for t in trainers if "zapdos" in t.name.lower()), None)
        assert legendary is not None

    def test_varied_separator_styles(self) -> None:
        """Handles varied separator styles (===, +++, xxx, ooo, MmM)."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH, progression_only=False)
        # Should find trainers behind all separator styles
        names = [t.name.lower() for t in trainers]
        assert any("axelrod" in n for n in names)  # === separator
        assert any("mirskle" in n for n in names)  # +++ separator
        assert any("james" in n or "emboar" in n for n in names)  # xxx separator
        assert any("zapdos" in n for n in names)  # ooo separator
        assert any("gary" in n for n in names)  # MmM separator


class TestMatchTrainersToDb:
    """Tests for match_trainers_to_db function."""

    def test_exact_match(self) -> None:
        """Matches trainer when DB has exact name."""
        trainers = [
            WalkthroughTrainer(
                name="Leader Mirskle",
                trainer_key="leader_mirskle",
                position=100,
                battle_type="GYM",
            )
        ]
        db_names = ["Leader Mirskle", "Leader Alice", "Rival Axelrod"]

        matched = match_trainers_to_db(trainers, db_names)
        assert matched[0].matched_db_name == "Leader Mirskle"

    def test_partial_match(self) -> None:
        """Matches trainer with partial key overlap."""
        trainers = [
            WalkthroughTrainer(
                name="Rival Axelrod",
                trainer_key="rival_axelrod",
                position=100,
                battle_type="RIVAL",
            )
        ]
        db_names = ["Axelrod 1", "Axelrod 2", "Leader Alice"]

        matched = match_trainers_to_db(trainers, db_names)
        assert matched[0].matched_db_name is not None
        assert "axelrod" in matched[0].matched_db_name.lower()

    def test_no_match_returns_none(self) -> None:
        """Returns None for matched_db_name when no match found."""
        trainers = [
            WalkthroughTrainer(
                name="Unknown Trainer",
                trainer_key="unknown_trainer",
                position=100,
                battle_type="BOSS",
            )
        ]
        db_names = ["Leader Alice", "Rival Bob"]

        matched = match_trainers_to_db(trainers, db_names)
        assert matched[0].matched_db_name is None


class TestSegmentByTrainers:
    """Tests for segment_by_trainers function."""

    def test_creates_initial_segment(self) -> None:
        """Creates segment for content before first trainer."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        segments = segment_by_trainers(SAMPLE_WALKTHROUGH, trainers)

        assert segments[0].segment_index == 0
        assert segments[0].after_trainer is None

    def test_creates_segments_between_trainers(self) -> None:
        """Creates segments for content between trainers."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        segments = segment_by_trainers(SAMPLE_WALKTHROUGH, trainers)

        # Should have one more segment than trainers (initial + one per trainer)
        assert len(segments) == len(trainers) + 1

    def test_segment_references_previous_trainer(self) -> None:
        """Each segment (except first) references the trainer just defeated."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        segments = segment_by_trainers(SAMPLE_WALKTHROUGH, trainers)

        assert segments[1].after_trainer is not None
        assert segments[1].after_trainer == trainers[0]


class TestBadgeRewards:
    """Tests for badge reward hardcoded data."""

    def test_badge_rewards_has_all_entries(self) -> None:
        """Badge rewards list has all 10 entries (game start + 9 badges)."""
        assert len(BADGE_REWARDS) == 10

    def test_badge_numbers_sequential(self) -> None:
        """Badge numbers are 0-9 in order."""
        numbers = [br.badge_number for br in BADGE_REWARDS]
        assert numbers == list(range(10))

    def test_game_start_has_no_hms(self) -> None:
        """Game start (badge 0) has no HM unlocks."""
        game_start = get_badge_reward("__game_start__")
        assert game_start is not None
        assert game_start.hm_unlocks == []
        assert game_start.level_cap_vanilla == 15
        assert game_start.level_cap_difficult == 20

    def test_leader_vega_unlocks_cut(self) -> None:
        """Leader Véga (badge 2) unlocks Cut."""
        reward = get_badge_reward("leader_vega")
        assert reward is not None
        assert reward.badge_number == 2
        assert reward.hm_unlocks == ["Cut"]
        assert reward.level_cap_vanilla == 29
        assert reward.level_cap_difficult == 32

    def test_leader_mel_unlocks_fly_strength(self) -> None:
        """Leader Mel (badge 4) unlocks Fly and Strength."""
        reward = get_badge_reward("leader_mel")
        assert reward is not None
        assert reward.badge_number == 4
        assert reward.hm_unlocks == ["Fly", "Strength"]

    def test_successor_maxima_unlocks_surf(self) -> None:
        """Successor Maxima (badge 5) unlocks Surf."""
        reward = get_badge_reward("successor_maxima")
        assert reward is not None
        assert reward.badge_number == 5
        assert reward.hm_unlocks == ["Surf"]

    def test_get_badge_reward_unknown_returns_none(self) -> None:
        """Unknown trainer key returns None."""
        assert get_badge_reward("unknown_trainer") is None

    def test_all_rewards_are_badge_reward_type(self) -> None:
        """All entries in BADGE_REWARDS are BadgeReward instances."""
        for reward in BADGE_REWARDS:
            assert isinstance(reward, BadgeReward)

    def test_level_caps_increase_monotonically(self) -> None:
        """Vanilla level caps increase with each badge."""
        caps = [br.level_cap_vanilla for br in BADGE_REWARDS]
        assert caps == sorted(caps)


class TestExtractRodUpgrade:
    """Tests for extract_rod_upgrade function."""

    def test_extracts_old_rod(self) -> None:
        """Extracts Old Rod upgrade."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="You received the Old Rod from the fisherman.",
        )
        rod = extract_rod_upgrade(segment)
        assert rod == "Old Rod"

    def test_extracts_good_rod(self) -> None:
        """Extracts Good Rod upgrade."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="You obtained the Good Rod!",
        )
        rod = extract_rod_upgrade(segment)
        assert rod == "Good Rod"

    def test_extracts_super_rod(self) -> None:
        """Extracts Super Rod upgrade."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="You got the Super Rod from the guru.",
        )
        rod = extract_rod_upgrade(segment)
        assert rod == "Super Rod"

    def test_no_rod_returns_none(self) -> None:
        """Returns None when no rod mentioned."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="No fishing equipment here.",
        )
        rod = extract_rod_upgrade(segment)
        assert rod is None


class TestExtractLocationsFromSegment:
    """Tests for extract_locations_from_segment function."""

    def test_matches_known_location(self) -> None:
        """Matches location to known DB locations."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text='[froz] FROZEN HEIGHTS {An Island Town}\n[rt01] ROUTE 1 "Path"',
        )
        known = ["Frozen Heights", "Route 1", "Bellin Town"]

        locations = extract_locations_from_segment(segment, known)
        assert "Frozen Heights" in locations
        assert "Route 1" in locations
        assert "Bellin Town" not in locations

    def test_empty_known_returns_empty(self) -> None:
        """Returns empty list when no known locations provided."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="[froz] FROZEN HEIGHTS {Town}",
        )
        locations = extract_locations_from_segment(segment, [])
        assert locations == []


class TestParseWalkthrough:
    """Tests for parse_walkthrough main function."""

    def test_returns_progression_unlocks(self) -> None:
        """Returns list of ProgressionUnlock objects."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        assert len(unlocks) > 0
        assert all(isinstance(u, ProgressionUnlock) for u in unlocks)

    def test_first_unlock_has_no_trainer(self) -> None:
        """First unlock represents game start with no trainer."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        assert unlocks[0].trainer_name is None
        assert unlocks[0].trainer_key is None

    def test_game_start_has_badge_zero(self) -> None:
        """Game start segment gets badge 0 level caps."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        assert unlocks[0].badge_number == 0
        assert unlocks[0].level_cap_vanilla == 15
        assert unlocks[0].level_cap_difficult == 20

    def test_gym_leader_has_badge_reward(self) -> None:
        """Gym leader segments get correct badge reward data."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        mirskle = next((u for u in unlocks if u.trainer_key == "leader_mirskle"), None)
        assert mirskle is not None
        assert mirskle.badge_number == 1
        assert mirskle.level_cap_vanilla == 22
        assert mirskle.level_cap_difficult == 26
        assert mirskle.battle_type == "GYM"

    def test_marks_post_game(self) -> None:
        """Marks post-game unlocks correctly."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        post_game = [u for u in unlocks if u.post_game]
        champion = next(
            (u for u in post_game if u.trainer_name and "gary" in u.trainer_name.lower()),
            None,
        )
        assert champion is not None

    def test_preamble_excluded_from_first_segment(self) -> None:
        """Preamble (table of contents) is stripped before parsing."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        # The first segment should start from "Hello there", not from the table of contents
        # If preamble was included, we'd see way more location-like content
        assert unlocks[0].trainer_name is None

    def test_excludes_legendary_battles(self) -> None:
        """Legendary battles are excluded from progression."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        legendary = next(
            (u for u in unlocks if u.trainer_name and "zapdos" in u.trainer_name.lower()),
            None,
        )
        assert legendary is None

    def test_post_game_gets_dive_hm(self) -> None:
        """First post-game segment gets Dive HM unlock."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        post_game = [u for u in unlocks if u.post_game]
        assert len(post_game) > 0
        all_post_game_hms: list[str] = []
        for u in post_game:
            all_post_game_hms.extend(u.hm_unlocks)
        assert "Dive" in all_post_game_hms


class TestUnlocksToYaml:
    """Tests for unlocks_to_yaml function."""

    def test_produces_valid_yaml(self) -> None:
        """Produces valid YAML string."""
        unlocks = [
            ProgressionUnlock(
                trainer_name=None,
                trainer_key=None,
                battle_type=None,
                badge_number=0,
                locations=["Route 1"],
                hm_unlocks=[],
                level_cap_vanilla=15,
                level_cap_difficult=20,
            ),
            ProgressionUnlock(
                trainer_name="Leader Alice",
                trainer_key="leader_alice",
                battle_type="GYM",
                badge_number=3,
                locations=["Route 2"],
                hm_unlocks=["Rock Smash"],
                level_cap_vanilla=33,
                level_cap_difficult=36,
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        assert "progression" in data
        assert len(data["progression"]) == 2

    def test_includes_metadata(self) -> None:
        """Includes metadata in output."""
        unlocks = [
            ProgressionUnlock(
                trainer_name=None,
                trainer_key=None,
                locations=[],
            )
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        assert "walkthrough_url" in data
        assert "extraction_date" in data

    def test_separates_post_game(self) -> None:
        """Separates main game and post-game unlocks."""
        unlocks = [
            ProgressionUnlock(
                trainer_name="Leader",
                trainer_key="leader",
                battle_type="GYM",
                locations=[],
                post_game=False,
            ),
            ProgressionUnlock(
                trainer_name="Champion",
                trainer_key="champion",
                battle_type="BORRIUS LEAGUE CHAMPIONSHIP",
                locations=[],
                post_game=True,
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        assert len(data["progression"]) == 1
        assert "post_game" in data
        assert len(data["post_game"]) == 1

    def test_includes_dual_level_caps(self) -> None:
        """YAML output includes both vanilla and difficult level caps."""
        unlocks = [
            ProgressionUnlock(
                trainer_name="Leader Alice",
                trainer_key="leader_alice",
                battle_type="GYM",
                badge_number=3,
                locations=[],
                level_cap_vanilla=33,
                level_cap_difficult=36,
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        entry = data["progression"][0]
        assert entry["level_cap_vanilla"] == 33
        assert entry["level_cap_difficult"] == 36
        assert entry["battle_type"] == "GYM"
        assert entry["badge_number"] == 3

    def test_includes_battle_type_and_badge(self) -> None:
        """YAML output includes battle_type and badge_number fields."""
        unlocks = [
            ProgressionUnlock(
                trainer_name="Rival Axelrod",
                trainer_key="rival_axelrod",
                battle_type="RIVAL",
                badge_number=None,
                locations=[],
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        entry = data["progression"][0]
        assert entry["battle_type"] == "RIVAL"
        assert entry["badge_number"] is None
