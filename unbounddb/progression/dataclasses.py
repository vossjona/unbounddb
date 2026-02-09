"""ABOUTME: Data classes for game progression extraction.
ABOUTME: Contains WalkthroughTrainer, ProgressionSegment, ProgressionUnlock, and BadgeReward."""

from dataclasses import dataclass, field


@dataclass
class WalkthroughTrainer:
    """A trainer found in the walkthrough with position for ordering.

    Attributes:
        name: The trainer name as it appears in the walkthrough (e.g., "Leader Alice").
        trainer_key: Slugified key for matching (e.g., "leader_alice").
        position: Character offset in walkthrough text for ordering.
        battle_type: The battle type (e.g., "GYM", "RIVAL", "SHADOW BOSS").
        matched_db_name: Name from DB if matched, None otherwise.
    """

    name: str
    trainer_key: str
    position: int
    battle_type: str
    matched_db_name: str | None = None


@dataclass
class ProgressionSegment:
    """A segment of walkthrough text between two important trainers.

    Attributes:
        segment_index: Zero-based index of this segment.
        after_trainer: The trainer that was just defeated, None for game start.
        text: The walkthrough content for this segment.
    """

    segment_index: int
    after_trainer: WalkthroughTrainer | None
    text: str


@dataclass
class ProgressionUnlock:
    """What becomes available after defeating a trainer.

    Attributes:
        trainer_name: The trainer that was defeated, None for game start.
        trainer_key: Slugified trainer key, None for game start.
        battle_type: The battle type (e.g., "GYM", "RIVAL"), None for game start.
        badge_number: Badge number (0-8) if applicable, None otherwise.
        locations: List of location names that become accessible.
        hm_unlocks: List of HM names that can now be used (e.g., ["Cut", "Surf"]).
        level_cap_vanilla: Level cap on vanilla difficulty, None if unchanged.
        level_cap_difficult: Level cap on difficult mode, None if unchanged.
        rod_upgrade: Rod obtained if any (e.g., "Old Rod", "Good Rod", "Super Rod").
        post_game: True if this is a post-game unlock.
    """

    trainer_name: str | None
    trainer_key: str | None
    battle_type: str | None = None
    badge_number: int | None = None
    locations: list[str] = field(default_factory=list)
    hm_unlocks: list[str] = field(default_factory=list)
    level_cap_vanilla: int | None = None
    level_cap_difficult: int | None = None
    rod_upgrade: str | None = None
    post_game: bool = False


@dataclass
class BadgeReward:
    """Hardcoded badge reward data mapping badges to level caps and HM unlocks.

    Attributes:
        badge_number: Badge number (0 = game start, 1-8 = gym badges).
        trainer_key: Slugified trainer key for lookup.
        level_cap_vanilla: Level cap on vanilla difficulty after this badge.
        level_cap_difficult: Level cap on difficult mode after this badge.
        hm_unlocks: List of HMs unlocked by this badge.
    """

    badge_number: int
    trainer_key: str
    level_cap_vanilla: int
    level_cap_difficult: int
    hm_unlocks: list[str] = field(default_factory=list)
