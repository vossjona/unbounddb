"""Contains logging related functionality."""

import logging
import logging.config
import typing
from pathlib import Path

import yaml


def init_logging(filepath: Path) -> dict[str, typing.Any]:  # pragma: no cover
    """Read logging config yaml file from `filepath` and initialize logging by applying it globally.

    :param filepath: Path to the logging configuration yaml file.
    :returns: The logging configuration as dict.
    """
    config: dict[str, typing.Any] = yaml.safe_load(filepath.read_text(encoding="utf-8"))
    logging.config.dictConfig(config)
    return config
