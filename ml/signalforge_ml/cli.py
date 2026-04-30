from __future__ import annotations

import json
from pathlib import Path

import typer

from signalforge_ml.config import load_config
from signalforge_ml.training import train_baseline

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def ingest(config_path: Path = Path("configs/baseline.yaml")) -> None:
    config = load_config(config_path)
    typer.echo(json.dumps(config["dataset"], indent=2))
    typer.echo("Dataset configuration loaded. Run train after placing a validated LINCS-style CSV in data/raw.")


@app.command()
def train(config_path: Path = Path("configs/baseline.yaml")) -> None:
    config = load_config(config_path)
    manifest = train_baseline(config)
    typer.echo(json.dumps(manifest, indent=2))