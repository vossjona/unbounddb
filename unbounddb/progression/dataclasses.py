"""ABOUTME: Data classes for game progression extraction.
ABOUTME: Contains WalkthroughTrainer, ProgressionSegment, and ProgressionUnlock."""

from dataclasses import dataclass, field


@dataclass
class WalkthroughTrainer:
    """A trainer found in the walkthrough with position for ordering.

    Attributes:
        name: The trainer name as it appears in the walkthrough (e.g., "Leader Alice").
        trainer_key: Slugified key for matching (e.g., "leader_alice").
        position: Character offset in walkthrough text for ordering.
        matched_db_name: Name from DB if matched, None otherwise.
    """

    name: str
    trainer_key: str
    position: int
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
        locations: List of location names that become accessible.
        hm_unlocks: List of HM names that can now be used (e.g., ["Cut", "Surf"]).
        level_cap: New level cap if changed, None if unchanged.
        rod_upgrade: Rod obtained if any (e.g., "Old Rod", "Good Rod", "Super Rod").
        post_game: True if this is a post-game unlock.
    """

    trainer_name: str | None
    trainer_key: str | None
    locations: list[str] = field(default_factory=list)
    hm_unlocks: list[str] = field(default_factory=list)
    level_cap: int | None = None
    rod_upgrade: str | None = None
    post_game: bool = False
