#!/usr/bin/env python
"""
SupplyMind — Data Generation CLI
Usage:
    python scripts/generate_synthetic_data.py --help
    python scripts/generate_synthetic_data.py --suppliers 500 --months 36
    python scripts/generate_synthetic_data.py --demand --skus 200 --days 1000
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from simulation.supplier_generator import SupplierDataGenerator, SupplierGeneratorConfig
from simulation.demand_generator import DemandSeriesGenerator
from config import settings

console = Console()
logging.basicConfig(level=logging.WARNING)


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────

@click.group()
def cli():
    """SupplyMind Data Generation Toolkit."""


@cli.command("suppliers")
@click.option("--n-suppliers", "-n", default=500, show_default=True,
              help="Number of synthetic suppliers to simulate.")
@click.option("--n-months", "-m", default=36, show_default=True,
              help="Number of months in each supplier's history.")
@click.option("--seed", default=42, show_default=True,
              help="Random seed for reproducibility.")
@click.option("--output", "-o", default=None,
              help="Output parquet file path. Defaults to data/synthetic/supplier_dataset.parquet.")
def generate_suppliers(n_suppliers: int, n_months: int, seed: int, output: str | None):
    """Generate synthetic supplier risk dataset."""
    out_path = Path(output) if output else Path(settings.synthetic_supplier_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = SupplierGeneratorConfig(
        n_suppliers=n_suppliers,
        n_months=n_months,
        random_seed=seed,
    )

    with Progress(SpinnerColumn(), "[progress.description]{task.description}",
                  TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Generating supplier data...", total=None)
        generator = SupplierDataGenerator(cfg)
        df = generator.generate()
        progress.update(task, description="[green]✓ Generation complete")

    df.to_parquet(out_path, index=False, engine="pyarrow")

    # Summary table
    table = Table(title="Supplier Dataset Summary", style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="yellow")
    table.add_row("Output path",       str(out_path))
    table.add_row("Rows",              f"{len(df):,}")
    table.add_row("Unique suppliers",  f"{df['supplier_id'].nunique():,}")
    table.add_row("Months",            str(df['month'].nunique()))
    table.add_row("Disruption rate",   f"{df['disrupted'].mean():.2%}")
    table.add_row("Features",          str(df.shape[1]))
    table.add_row("File size",         f"{out_path.stat().st_size / 1024:.1f} KB")
    console.print(table)
    console.print(f"\n[bold green]✓ Saved → {out_path}[/bold green]")


@cli.command("demand")
@click.option("--n-skus", "-n", default=200, show_default=True,
              help="Number of unique SKUs to generate.")
@click.option("--n-days", "-d", default=1800, show_default=True,
              help="Number of days in the time series.")
@click.option("--seed", default=42, show_default=True,
              help="Random seed for reproducibility.")
@click.option("--output", "-o", default=None,
              help="Output parquet path. Defaults to data/synthetic/demand_series.parquet.")
def generate_demand(n_skus: int, n_days: int, seed: int, output: str | None):
    """Generate synthetic demand time-series for TFT training."""
    out_path = Path(output) if output else Path(settings.data_synthetic_dir) / "demand_series.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with Progress(SpinnerColumn(), "[progress.description]{task.description}",
                  TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Generating demand time-series...", total=None)
        gen = DemandSeriesGenerator(n_skus=n_skus, n_days=n_days, random_seed=seed)
        df = gen.generate()
        progress.update(task, description="[green]✓ Generation complete")

    df.to_parquet(out_path, index=False, engine="pyarrow")

    table = Table(title="Demand Dataset Summary", style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="yellow")
    table.add_row("Output path",   str(out_path))
    table.add_row("Rows",          f"{len(df):,}")
    table.add_row("Unique SKUs",   f"{df['sku_id'].nunique():,}")
    table.add_row("Date range",    f"{df['date'].min()} → {df['date'].max()}")
    table.add_row("Avg demand",    f"{df['demand'].mean():.1f} units/day")
    table.add_row("Stockout rate", f"{df['stockout_flag'].mean():.2%}")
    table.add_row("File size",     f"{out_path.stat().st_size / 1024:.1f} KB")
    console.print(table)
    console.print(f"\n[bold green]✓ Saved → {out_path}[/bold green]")


@cli.command("all")
@click.pass_context
def generate_all(ctx):
    """Generate all synthetic datasets (suppliers + demand)."""
    console.print("[bold cyan]=== SupplyMind Data Generation ===[/bold cyan]\n")
    ctx.invoke(generate_suppliers)
    console.print()
    ctx.invoke(generate_demand)
    console.print("\n[bold green]All datasets generated successfully![/bold green]")


if __name__ == "__main__":
    cli()
