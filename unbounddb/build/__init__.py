"""ABOUTME: Build module for data transformation and database loading.
ABOUTME: Converts raw CSVs to normalized Parquet and loads into DuckDB."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unbounddb.build.pipeline import (
        run_build_pipeline as run_build_pipeline,
    )
    from unbounddb.build.pipeline import (
        run_github_build_pipeline as run_github_build_pipeline,
    )


def __getattr__(name: str) -> object:
    """Lazy-import pipeline functions to avoid loading Polars at import time."""
    if name in ("run_build_pipeline", "run_github_build_pipeline"):
        from unbounddb.build.pipeline import (  # noqa: PLC0415
            run_build_pipeline,
            run_github_build_pipeline,
        )

        return run_build_pipeline if name == "run_build_pipeline" else run_github_build_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["run_build_pipeline", "run_github_build_pipeline"]
