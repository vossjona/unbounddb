"""Contains configurations for the test run."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def resources_folder() -> Path:
    """Returns the path to the test resources folder."""
    return Path(__file__).parents[1] / "resources"
