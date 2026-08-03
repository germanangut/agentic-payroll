import json

import pytest
from typer.testing import CliRunner

from agentic_nomina.cli import app
from agentic_nomina.demo import DEMO_NOTICE, DEMO_PERIOD, run_demo


def test_demo_generates_valid_synthetic_artifacts(tmp_path) -> None:
    root = tmp_path / "demo"
    summary = run_demo(root, run_id="DEMO-TEST")
    assert summary["business_period"] == DEMO_PERIOD
    assert summary["run_id"] == "DEMO-TEST"
    assert summary["validation"] == "OK"
    assert (root / "manifest.yml").exists()
    assert (root / "results" / "agentic-nomina-demo.xlsx").exists()
    persisted = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert persisted["notice"] == DEMO_NOTICE
    assert str(root) not in json.dumps(persisted)
    assert {"Ejecucion", "Excepciones", "Revisiones", "Casos_Empleado", "Reglas", "Ausencias"} <= set(summary["sheets"])


def test_demo_rejects_nonempty_output_and_invalid_period(tmp_path) -> None:
    root = tmp_path / "occupied"
    root.mkdir()
    marker = root / "keep.txt"
    marker.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="vacío"):
        run_demo(root)
    assert marker.read_text(encoding="utf-8") == "do not overwrite"
    with pytest.raises(ValueError, match="YYYY-MM"):
        run_demo(tmp_path / "invalid", period="2099-13")
    assert not (tmp_path / "invalid").exists()


def test_demo_cli_is_public_and_keeps_explicit_metadata(tmp_path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0 and "demo" in help_result.output
    result = runner.invoke(app, ["demo", "--output-dir", str(tmp_path / "cli"), "--period", "2099-02", "--run-id", "DEMO-CLI"])
    assert result.exit_code == 0
    assert "DEMO-CLI" in result.output
