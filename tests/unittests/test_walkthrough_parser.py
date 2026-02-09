"""ABOUTME: Tests for walkthrough parser progression extraction.
ABOUTME: Verifies trainer extraction, segmentation, and unlock detection."""

import yaml

from unbounddb.progression.dataclasses import (
    ProgressionSegment,
    ProgressionUnlock,
    WalkthroughTrainer,
)
from unbounddb.progression.walkthrough_parser import (
    extract_hm_unlocks,
    extract_level_cap,
    extract_locations_from_segment,
    extract_rod_upgrade,
    find_important_trainers,
    match_trainers_to_db,
    parse_walkthrough,
    segment_by_trainers,
    unlocks_to_yaml,
)

# Sample walkthrough content for testing (matches actual walkthrough format)
SAMPLE_WALKTHROUGH = """
Pokemon Unbound Walkthrough

[froz] FROZEN HEIGHTS {An Island Town on a Frozen Lake.}
Starting area with Pokemon up to level 10.
Traded Pokemon will now obey us until Lv15.

[rt01] ROUTE 1 "Snowy Mountain Pass"
Wild Pokemon available.

>>RIVAL BATTLE<<
================

Rival Axelrod
- Lv12 Swinub [Ice/Ground]
- Lv13 Pikachu [Electric]

After the battle, we can now use Cut, great :)

[bell] BELLIN TOWN {A Quiet Town}
Get your first badge here!

>>GYM BATTLE<<
++++++++++++++

Leader Mirskle
- Lv18 Florges [Fairy]
- Lv20 Roserade [Grass/Poison]

Congratulations! Traded Pokemon will now obey us up to Lv30.
You also received the Old Rod from the fisherman.

[rt02] ROUTE 2 "Forest Path"
Many grass types here.

>>SHADOW BOSS BATTLE<<
======================

Black Emboar James
- Lv26 Koffing [Poison]

After defeating the boss, we can now use Surf on the water.

\\//[[POST-GAME ARC]]\\//

[post1] POST GAME AREA
This is post-game content.

>>CHAMPION BATTLE<<
===================

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

    def test_finds_leader_trainer(self) -> None:
        """Extracts leader trainer from walkthrough."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        leader = next((t for t in trainers if "leader" in t.name.lower()), None)
        assert leader is not None
        assert "mirskle" in leader.name.lower()
        assert leader.trainer_key == "leader_mirskle"

    def test_finds_boss_trainer(self) -> None:
        """Extracts boss trainer from walkthrough."""
        trainers = find_important_trainers(SAMPLE_WALKTHROUGH)
        boss = next(
            (t for t in trainers if "james" in t.name.lower() or "emboar" in t.name.lower()),
            None,
        )
        assert boss is not None

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


class TestMatchTrainersToDb:
    """Tests for match_trainers_to_db function."""

    def test_exact_match(self) -> None:
        """Matches trainer when DB has exact name."""
        trainers = [
            WalkthroughTrainer(
                name="Leader Mirskle",
                trainer_key="leader_mirskle",
                position=100,
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
            )
        ]
        db_names = ["Axelrod 1", "Axelrod 2", "Leader Alice"]

        matched = match_trainers_to_db(trainers, db_names)
        # Should match on "axelrod" substring
        assert matched[0].matched_db_name is not None
        assert "axelrod" in matched[0].matched_db_name.lower()

    def test_no_match_returns_none(self) -> None:
        """Returns None for matched_db_name when no match found."""
        trainers = [
            WalkthroughTrainer(
                name="Unknown Trainer",
                trainer_key="unknown_trainer",
                position=100,
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

        # First segment should have no after_trainer
        assert segments[0].segment_index == 0
        assert segments[0].after_trainer is None
        assert "[froz]" in segments[0].text

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

        # Second segment should reference first trainer
        assert segments[1].after_trainer is not None
        assert segments[1].after_trainer == trainers[0]


class TestExtractHmUnlocks:
    """Tests for extract_hm_unlocks function."""

    def test_extracts_cut(self) -> None:
        """Extracts Cut HM unlock."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="After the battle, we can now use Cut, great :)",
        )
        hms = extract_hm_unlocks(segment)
        assert "Cut" in hms

    def test_extracts_surf(self) -> None:
        """Extracts Surf HM unlock."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="we can now use Surf on the water",
        )
        hms = extract_hm_unlocks(segment)
        assert "Surf" in hms

    def test_extracts_rock_smash(self) -> None:
        """Extracts Rock Smash HM unlock."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="we can now use Rock Smash to break rocks",
        )
        hms = extract_hm_unlocks(segment)
        assert "Rock Smash" in hms

    def test_no_hm_returns_empty(self) -> None:
        """Returns empty list when no HM mentions."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="Just regular text with no HM unlocks.",
        )
        hms = extract_hm_unlocks(segment)
        assert hms == []


class TestExtractLevelCap:
    """Tests for extract_level_cap function."""

    def test_extracts_until_format(self) -> None:
        """Extracts level cap with 'until' format."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="Traded Pokemon will now obey us until Lv15.",
        )
        cap = extract_level_cap(segment)
        assert cap == 15

    def test_extracts_up_to_format(self) -> None:
        """Extracts level cap with 'up to' format."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="Traded Pokemon will now obey us up to Lv30.",
        )
        cap = extract_level_cap(segment)
        assert cap == 30

    def test_no_cap_returns_none(self) -> None:
        """Returns None when no level cap mention."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="Just regular text.",
        )
        cap = extract_level_cap(segment)
        assert cap is None

    def test_multiple_caps_returns_last(self) -> None:
        """Returns last (highest) cap when multiple mentioned."""
        segment = ProgressionSegment(
            segment_index=0,
            after_trainer=None,
            text="First obey us until Lv15. Later obey us up to Lv30.",
        )
        cap = extract_level_cap(segment)
        assert cap == 30


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

    def test_extracts_level_caps(self) -> None:
        """Extracts level cap changes from walkthrough."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        level_caps = [u.level_cap for u in unlocks if u.level_cap is not None]
        assert 15 in level_caps
        assert 30 in level_caps

    def test_extracts_hm_unlocks(self) -> None:
        """Extracts HM unlocks from walkthrough."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        all_hms = []
        for u in unlocks:
            all_hms.extend(u.hm_unlocks)
        assert "Cut" in all_hms
        assert "Surf" in all_hms

    def test_marks_post_game(self) -> None:
        """Marks post-game unlocks correctly."""
        unlocks = parse_walkthrough(SAMPLE_WALKTHROUGH)
        post_game = [u for u in unlocks if u.post_game]
        # Champion Gary should be in post-game
        champion = next((u for u in post_game if u.trainer_name and "gary" in u.trainer_name.lower()), None)
        assert champion is not None


class TestUnlocksToYaml:
    """Tests for unlocks_to_yaml function."""

    def test_produces_valid_yaml(self) -> None:
        """Produces valid YAML string."""
        unlocks = [
            ProgressionUnlock(
                trainer_name=None,
                trainer_key=None,
                locations=["Route 1"],
                hm_unlocks=[],
                level_cap=15,
            ),
            ProgressionUnlock(
                trainer_name="Leader Alice",
                trainer_key="leader_alice",
                locations=["Route 2"],
                hm_unlocks=["Cut"],
                level_cap=25,
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        # Should be parseable
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
                locations=[],
                post_game=False,
            ),
            ProgressionUnlock(
                trainer_name="Champion",
                trainer_key="champion",
                locations=[],
                post_game=True,
            ),
        ]

        yaml_str = unlocks_to_yaml(unlocks)
        data = yaml.safe_load(yaml_str)
        assert len(data["progression"]) == 1
        assert "post_game" in data
        assert len(data["post_game"]) == 1
