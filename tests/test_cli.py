from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_joinery import Pipeline
from data_joinery.cli import app


@pytest.fixture
def pipeline_file(tmp_path: Path) -> Path:
    path = tmp_path / "example_pipeline.py"
    path.write_text(
        """from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from data_joinery import Context, Pipeline, side_effect, transform

@dataclass
class RunContext:
    destination: Path

    @classmethod
    def from_kwargs(cls, *, destination: str):
        return cls(Path(destination))

@transform
def produce(destination: Annotated[Path, Context()]) -> str:
    destination.write_text('produce')
    return 'value'

@side_effect
def publish(value: str, destination: Annotated[Path, Context()]) -> None:
    destination.write_text(destination.read_text() + ',publish')

def build_pipeline():
    pipeline = Pipeline(RunContext)
    pipeline.add_step(produce) >> pipeline.add_step(publish)
    return pipeline
"""
    )
    return path


def test_run_executes_side_effects(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"
    result = CliRunner().invoke(
        app, ["run", str(pipeline_file), "--context", f"destination={destination}"]
    )

    assert (result.exit_code, destination.read_text()) == (0, "produce,publish")


def test_run_reports_start_and_completion(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"

    result = CliRunner().invoke(
        app, ["run", str(pipeline_file), "--context", f"destination={destination}"]
    )

    assert result.output == (
        f"Running pipeline from {pipeline_file}...\nPipeline finished.\n"
    )


def test_run_does_not_report_completion_after_failure(
    pipeline_file: Path, tmp_path: Path, monkeypatch
):
    def fail(*args, **kwargs):
        raise RuntimeError("step failed")

    monkeypatch.setattr(Pipeline, "run", fail)
    destination = tmp_path / "run.txt"

    result = CliRunner().invoke(
        app, ["run", str(pipeline_file), "--context", f"destination={destination}"]
    )

    assert result.output == f"Running pipeline from {pipeline_file}...\n"


def test_run_skips_side_effects(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"
    result = CliRunner().invoke(
        app,
        [
            "run",
            str(pipeline_file),
            "--context",
            f"destination={destination}",
            "--skip-side-effects",
        ],
    )

    assert (result.exit_code, destination.read_text()) == (0, "produce")


@pytest.mark.parametrize("extension", ["png", "svg"])
def test_visualize_saves_figure(pipeline_file: Path, tmp_path: Path, extension: str):
    pytest.importorskip("matplotlib")
    output = tmp_path / f"pipeline.{extension}"

    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(output)]
    )

    assert result.exit_code == 0 and output.stat().st_size > 1000


def test_visualize_reports_saved_file(pipeline_file: Path, tmp_path: Path):
    pytest.importorskip("matplotlib")
    output = tmp_path / "pipeline.svg"

    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(output)]
    )

    assert result.output == (
        f"Visualizing pipeline from {pipeline_file}...\n"
        f"Pipeline visualization saved to {output}.\n"
    )


def test_visualize_reports_displayed_figure(pipeline_file: Path, monkeypatch):
    pyplot = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(pyplot, "show", lambda: None)

    result = CliRunner().invoke(app, ["visualize", str(pipeline_file)])

    assert result.output == (
        f"Visualizing pipeline from {pipeline_file}...\n"
        "Pipeline visualization displayed.\n"
    )


def test_visualize_rejects_unsupported_format(pipeline_file: Path, tmp_path: Path):
    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(tmp_path / "x.pdf")]
    )

    assert result.exit_code != 0 and "svg or .png" in result.output


def test_run_rejects_malformed_context(pipeline_file: Path):
    result = CliRunner().invoke(app, ["run", str(pipeline_file), "--context", "bad"])

    assert result.exit_code != 0 and "NAME=VALUE" in result.output


def test_run_uses_main_py_by_default(tmp_path: Path, monkeypatch):
    (tmp_path / "main.py").write_text(
        "from data_joinery import Pipeline\npipeline = Pipeline()\n"
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["run"])

    assert result.exit_code == 0


def test_run_accepts_module_and_explicit_builder(
    pipeline_file: Path, tmp_path: Path, monkeypatch
):
    monkeypatch.syspath_prepend(str(pipeline_file.parent))
    destination = tmp_path / "module.txt"

    result = CliRunner().invoke(
        app,
        [
            "run",
            "example_pipeline:build_pipeline",
            "--context",
            f"destination={destination}",
        ],
    )

    assert (result.exit_code, destination.read_text()) == (0, "produce,publish")


def test_run_loads_file_inside_package(tmp_path: Path):
    package = tmp_path / "pipeline_package"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "steps.py").write_text(
        "from data_joinery import Pipeline\npipeline = Pipeline()\n"
    )
    target = package / "main.py"
    target.write_text("from .steps import pipeline\n")

    result = CliRunner().invoke(app, ["run", str(target)])

    assert result.exit_code == 0
