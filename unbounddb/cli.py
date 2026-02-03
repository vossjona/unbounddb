"""ABOUTME: CLI entry point for unbounddb commands.
ABOUTME: Provides fetch, build, and ui commands via Typer."""

import asyncio
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import typer
from rich.console import Console

from unbounddb.build import run_build_pipeline, run_github_build_pipeline
from unbounddb.ingestion import (
    fetch_all_external_sources,
    fetch_all_github_sources,
    fetch_all_tabs,
    validate_manual_csvs,
)
from unbounddb.settings import settings

app = typer.Typer(
    name="unbounddb",
    help="Pokemon Unbound data pipeline and query tool.",
    no_args_is_help=True,
)

console = Console()


def _print_paths(paths: Mapping[str, Path | list[Path]], label: str) -> None:
    """Print fetched/found paths."""
    # Count total items (files or directories with their file counts)
    total_count = 0
    for value in paths.values():
        if isinstance(value, list):
            total_count += len(value)
        else:
            total_count += 1

    console.print(f"[green]{label} {total_count} items across {len(paths)} sources:[/]")
    for name, path in paths.items():
        if isinstance(path, list):
            console.print(f"  {name}: {len(path)} files")
        else:
            console.print(f"  {name}: {path}")


def _fetch_manual(verbose: bool) -> None:
    """Validate manual CSVs."""
    if verbose:
        console.print(f"[blue]Validating manual CSVs in {settings.raw_manual_dir}[/]")
    try:
        paths = validate_manual_csvs()
        _print_paths(paths, "Found")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1) from None


def _fetch_github(force: bool, verbose: bool) -> None:
    """Fetch from GitHub and external sources."""
    if verbose:
        suffix = " (force refresh)" if force else ""
        console.print(f"[blue]Fetching C source files to {settings.raw_github_dir}{suffix}[/]")
    try:
        paths = asyncio.run(fetch_all_github_sources(force=force))
        _print_paths(paths, "Fetched")
    except Exception as e:
        console.print(f"[red]Error fetching data:[/] {e}")
        raise typer.Exit(1) from None

    # Also fetch external sources (trainer data)
    if verbose:
        console.print(f"[blue]Fetching external sources to {settings.raw_github_dir}{suffix}[/]")
    try:
        external_paths = asyncio.run(fetch_all_external_sources(force=force))
        _print_paths(external_paths, "Fetched")
    except Exception as e:
        console.print(f"[red]Error fetching external data:[/] {e}")
        raise typer.Exit(1) from None


def _fetch_sheets(force: bool, verbose: bool) -> None:
    """Fetch from Google Sheets."""
    if verbose:
        suffix = " (force refresh)" if force else ""
        console.print(f"[blue]Fetching CSVs to {settings.raw_exports_dir}{suffix}[/]")
    try:
        paths = asyncio.run(fetch_all_tabs(force=force))
        _print_paths(paths, "Fetched")
    except Exception as e:
        console.print(f"[red]Error fetching data:[/] {e}")
        raise typer.Exit(1) from None


@app.command()
def fetch(
    force: bool = typer.Option(False, "--force", "-f", help="Re-download cached files"),
    manual: bool = typer.Option(False, "--manual", "-m", help="Validate manual CSVs instead of fetching"),
    github: bool = typer.Option(False, "--github", "-g", help="Fetch from GitHub C source files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Fetch data from Google Sheets, GitHub, or validate manual CSVs."""
    if manual:
        _fetch_manual(verbose)
    elif github:
        _fetch_github(force, verbose)
    else:
        _fetch_sheets(force, verbose)


@app.command()
def build(
    manual: bool = typer.Option(False, "--manual", "-m", help="Use manual CSVs as source"),
    github: bool = typer.Option(False, "--github", "-g", help="Use GitHub C source files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Transform data to Parquet and load into DuckDB."""

    def log(msg: str) -> None:
        if verbose:
            console.print(f"[blue]{msg}[/]")

    try:
        if github:
            db_path = run_github_build_pipeline(
                source_dir=settings.raw_github_dir,
                verbose_callback=log,
            )
        else:
            source_dir = settings.raw_manual_dir if manual else settings.raw_exports_dir
            db_path = run_build_pipeline(source_dir=source_dir, verbose_callback=log)
        console.print(f"[green]Database built successfully:[/] {db_path}")
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Build failed:[/] {e}")
        raise typer.Exit(1) from None


@app.command()
def ui(
    port: int = typer.Option(8501, "--port", "-p", help="Port for Streamlit server"),
) -> None:
    """Launch the Streamlit query UI."""
    app_path = Path(__file__).parent / "app" / "main.py"

    if not app_path.exists():
        console.print(f"[red]Error:[/] Streamlit app not found at {app_path}")
        raise typer.Exit(1)

    if not settings.db_path.exists():
        console.print(f"[yellow]Warning:[/] Database not found at {settings.db_path}. Run 'unbounddb build' first.")

    console.print(f"[blue]Starting Streamlit UI on port {port}...[/]")

    try:
        # All arguments are controlled/validated - not user-provided strings
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
            check=True,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]UI stopped.[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Streamlit failed:[/] {e}")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
