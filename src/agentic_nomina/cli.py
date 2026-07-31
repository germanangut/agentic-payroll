from __future__ import annotations

from pathlib import Path

import typer

from agentic_nomina.config import load_config
from agentic_nomina.service import run_baseline

app = typer.Typer(help="Agentic Nomina reconciliation baseline.")


@app.command("reconcile")
def reconcile(
    payroll_q1: Path = typer.Option(..., exists=True, help="First payroll period Excel file."),
    payroll_q2: Path = typer.Option(..., exists=True, help="Second payroll period Excel file."),
    employees_q1: Path = typer.Option(..., exists=True, help="First employee list Excel file."),
    employees_q2: Path = typer.Option(..., exists=True, help="Second employee list Excel file."),
    pila: Path = typer.Option(..., exists=True, help="Monthly PILA Excel file."),
    output: Path = typer.Option(Path("data/processed/reconciliation.xlsx")),
    config_path: Path = typer.Option(Path("config/baseline.yml"), "--config"),
) -> None:
    config = load_config(config_path)
    results = run_baseline(
        payroll_q1_path=payroll_q1,
        payroll_q2_path=payroll_q2,
        employees_q1_path=employees_q1,
        employees_q2_path=employees_q2,
        pila_path=pila,
        output_path=output,
        config=config,
    )
    typer.echo(f"Report written to {output}")
    typer.echo(f"Q1 employee controls: {len(results['Q1'])}")
    typer.echo(f"Q2 employee controls: {len(results['Q2'])}")
    typer.echo(f"Social security employees: {len(results['social_security'])}")


if __name__ == "__main__":
    app()
