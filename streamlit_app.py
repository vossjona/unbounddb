"""ABOUTME: Entry point for Streamlit Community Cloud deployment.
ABOUTME: Delegates to the main app module."""

import traceback

import streamlit as st

st.write("DIAG 1: entry script executing")

try:
    import unbounddb.app.main  # noqa: F401
except Exception:
    st.error("Unhandled exception — this message is from the diagnostic wrapper.")
    st.code(traceback.format_exc())

st.write("DIAG 2: import completed (no exception)")
