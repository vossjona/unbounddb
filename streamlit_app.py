"""ABOUTME: Entry point for Streamlit Community Cloud deployment.
ABOUTME: Forces fresh module execution on every Streamlit rerun."""

import sys

# Remove cached module so the import re-executes module-level code on every
# Streamlit rerun.  Without this, Python's import cache makes the import a
# no-op after the first load, resulting in a blank page on interaction.
sys.modules.pop("unbounddb.app.main", None)

import unbounddb.app.main  # noqa: F401, E402
