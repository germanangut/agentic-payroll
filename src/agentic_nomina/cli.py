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
        Path | None,
        typer.Option(help="Primer archivo de nómina (o declararlo en --manifest)."),
    ] = None,
    payroll_q2: Annotated[
        Path | None,
        typer.Option(help="Segundo archivo de nómina (o declararlo en --manifest)."),
    ] = None,
    employees_q1: Annotated[
        Path | None,
        typer.Option(help="Primera lista de empleados (o declararla en --manifest)."),
    ] = None,
    employees_q2: Annotated[
        Path | None,
        typer.Option(help="Segunda lista de empleados (o declararla en --manifest)."),
    ] = None,
    pila: Annotated[
        Path | None,
        typer.Option(help="Archivo PILA mensual (o declararlo en --manifest)."),
    ] = None,
    overtime_q1: Annotated[
        Path | None,
        typer.Option(exists=True, help="First-period overtime source workbook."),
    ] = None,
    overtime_q2: Annotated[
        Path | None,
        typer.Option(exists=True, help="Second-period overtime source workbook."),
    ] = None,
    los_olivos: Annotated[
        Path | None,
        typer.Option(exists=True, help="Monthly Los Olivos affiliate invoice PDF."),
    ] = None,
    comfatolima: Annotated[
        Path | None,
        typer.Option(exists=True, help="Monthly Comfatolima credit report PDF."),
    ] = None,
    loans_q1: Annotated[
        Path | None,
        typer.Option(exists=True, help="First-period Siigo employee-loan balance PDF."),
    ] = None,
    loans_q2: Annotated[
        Path | None,
        typer.Option(exists=True, help="Second-period Siigo employee-loan balance PDF."),
    ] = None,
    reviews: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            help="Previous reconciliation workbook or CSV with human review decisions.",
        ),
    ] = None,
    rules: Annotated[
        Path | None,
        typer.Option(exists=True, help="Previous workbook or CSV with rule approvals."),
    ] = None,
    require_approved_rules: Annotated[
        bool,
        typer.Option("--require-approved-rules", help="Block runs with unapproved active financial rules."),
    ] = False,
    absence_evidence: Annotated[list[Path] | None, typer.Option("--absence-evidence", exists=True, help="Absence evidence PDF or normalized CSV; may be repeated.")] = None,
    period: Annotated[str | None, typer.Option("--period", help="Business period in YYYY-MM format.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Auditable run identifier.")] = None,
    manifest: Annotated[Path | None, typer.Option("--manifest", exists=True, help="Manifiesto YAML técnico de la corrida.")] = None,
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
        los_olivos_path=los_olivos,
        comfatolima_path=comfatolima,
        loans_q1_path=loans_q1,
        loans_q2_path=loans_q2,
        reviews_path=reviews,
        rules_path=rules,
        require_approved_rules=require_approved_rules,
        absence_evidence_paths=absence_evidence or [],
        business_period=period,
        run_id=run_id,
        manifest_path=manifest,
        output_path=output,
        config=config,
    )
    typer.echo(f"Report written to {output}")
    typer.echo(f"Q1 employee controls: {len(results['Q1'])}")
    typer.echo(f"Q2 employee controls: {len(results['Q2'])}")
    typer.echo(f"Social security employees: {len(results['social_security'])}")
    if "overtime" in results:
        typer.echo(f"Overtime employee-period controls: {len(results['overtime'])}")
    if "los_olivos" in results:
        typer.echo(f"Los Olivos employee controls: {len(results['los_olivos'])}")
    if "comfatolima" in results:
        typer.echo(f"Comfatolima employee controls: {len(results['comfatolima'])}")
    if "loans" in results:
        typer.echo(f"Employee-loan balance controls: {len(results['loans'])}")


if __name__ == "__main__":
    app()
