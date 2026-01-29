"""This module contains configuration logic for this project."""

from pydantic_settings import BaseSettings

from unbounddb import __version__


class Settings(BaseSettings):
    """Contains settings for this project."""
    VERSION: str = __version__
    """Project version."""
