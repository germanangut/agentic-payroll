from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agentic_nomina.config import load_config
from agentic_nomina.service import run_baseline

app = typer.Typer(help="Agentic Nomina reconciliation baseline.")


@app.callback()
def main() -> None:
    """Run Agentic Nomina commands."""


@app.command("reconcile")
def reconcile(
    payroll_q1: Annotated[
        Path,
        typer.Option(exists=True, help="First payroll period Excel file."),
    ],
    payroll_q2: Annotated[
        Path,
        typer.Option(exists=True, help="Second payroll period Excel file."),
    ],
    employees_q1: Annotated[
        Path,
        typer.Option(exists=True, help="First employee list Excel file."),
    ],
    employees_q2: Annotated[
        Path,
        typer.Option(exists=True, help="Second employee list Excel file."),
    ],
    pila: Annotated[
        Path,
        typer.Option(exists=True, help="Monthly PILA Excel file."),
    ],
    overtime_q1: Annotated[
        Path | None,
        typer.Option(exists=True, help="First-period overtime source workbook."),
    ] = None,
    overtime_q2: Annotated[
        Path | None,
        typer.Option(exists=True, help="Second-period overtime source workbook."),
    ] = None,
    output: Annotated[Path, typer.Option()] = Path("data/processed/reconciliation.xlsx"),
    config_path: Annotated[Path, typer.Option("--config")] = Path("config/baseline.yml"),
) -> None:
    config = load_config(config_path)
    results = run_baseline(
        payroll_q1_path=payroll_q1,
        payroll_q2_path=payroll_q2,
        employees_q1_path=employees_q1,
        employees_q2_path=employees_q2,
        pila_path=pila,
        overtime_q1_path=overtime_q1,
        overtime_q2_path=overtime_q2,
        output_path=output,
        config=config,
    )
    typer.echo(f"Report written to {output}")
    typer.echo(f"Q1 employee controls: {len(results['Q1'])}")
    typer.echo(f"Q2 employee controls: {len(results['Q2'])}")
    typer.echo(f"Social security employees: {len(results['social_security'])}")
    if "overtime" in results:
        typer.echo(f"Overtime employee-period controls: {len(results['overtime'])}")


if __name__ == "__main__":
    app()
