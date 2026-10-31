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
from data_joinery import Context, Job, Pipeline, side_effect, transform

@dataclass
class RunContext:
    destination: Path


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

job = Job(pipeline=build_pipeline())

@job.context()
def context(destination: Path) -> RunContext:
    return RunContext(destination)

def build_job():
    return job

if __name__ == "__main__":
    job()
"""
    )
    return path


def test_run_executes_side_effects(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"
    result = CliRunner().invoke(app, ["run", str(pipeline_file), str(destination)])

    assert result.exit_code == 0
    assert destination.read_text() == "produce,publish"


def test_run_reports_start_and_completion(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"

    result = CliRunner().invoke(app, ["run", str(pipeline_file), str(destination)])

    assert result.output == ("Running pipeline...\nPipeline finished.\n")


def test_run_does_not_report_completion_after_failure(
    pipeline_file: Path, tmp_path: Path, monkeypatch
):
    def fail(*args, **kwargs):
        raise RuntimeError("step failed")

    monkeypatch.setattr(Pipeline, "run", fail)
    destination = tmp_path / "run.txt"

    result = CliRunner().invoke(app, ["run", str(pipeline_file), str(destination)])

    assert result.output == "Running pipeline...\n"


def test_run_skips_side_effects(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "run.txt"
    result = CliRunner().invoke(
        app,
        [
            "run",
            str(pipeline_file),
            str(destination),
            "--skip-side-effects",
        ],
    )

    assert result.exit_code == 0
    assert destination.read_text() == "produce"


@pytest.mark.parametrize("extension", ["png", "svg"])
def test_visualize_saves_figure(pipeline_file: Path, tmp_path: Path, extension: str):
    pytest.importorskip("matplotlib")
    output = tmp_path / f"pipeline.{extension}"

    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(output)]
    )

    assert result.exit_code == 0
    assert output.stat().st_size > 1000


def test_visualize_reports_saved_file(pipeline_file: Path, tmp_path: Path):
    pytest.importorskip("matplotlib")
    output = tmp_path / "pipeline.svg"

    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(output)]
    )

    assert result.output == (
        f"Visualizing pipeline...\nPipeline visualization saved to {output}.\n"
    )


def test_visualize_reports_displayed_figure(pipeline_file: Path, monkeypatch):
    pyplot = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(pyplot, "show", lambda: None)

    result = CliRunner().invoke(app, ["visualize", str(pipeline_file)])

    assert result.output == (
        "Visualizing pipeline...\nPipeline visualization displayed.\n"
    )


def test_visualize_rejects_unsupported_format(pipeline_file: Path, tmp_path: Path):
    result = CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(tmp_path / "x.pdf")]
    )

    assert result.exit_code != 0
    assert "svg or .png" in result.output


def test_run_uses_main_py_by_default(tmp_path: Path, monkeypatch):
    (tmp_path / "main.py").write_text(
        "from data_joinery import Job, Pipeline\njob = Job(pipeline=Pipeline())\n"
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
            "example_pipeline:build_job",
            str(destination),
        ],
    )

    assert result.exit_code == 0
    assert destination.read_text() == "produce,publish"


def test_run_loads_file_inside_package(tmp_path: Path):
    package = tmp_path / "pipeline_package"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "steps.py").write_text(
        "from data_joinery import Job, Pipeline\njob = Job(pipeline=Pipeline())\n"
    )
    target = package / "main.py"
    target.write_text("from .steps import job\n")

    result = CliRunner().invoke(app, ["run", str(target)])

    assert result.exit_code == 0


def test_target_specific_help_contains_application_options(pipeline_file: Path):
    result = CliRunner().invoke(app, ["run", str(pipeline_file), "--help"])

    assert "destination" in result.output
    assert result.exit_code == 0


@pytest.mark.parametrize("arguments", [["--help"], ["run", "--help"]])
def test_launcher_help_never_imports_default_module(tmp_path, monkeypatch, arguments):
    (tmp_path / "main.py").write_text("raise AssertionError('must not import')\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0


def test_default_builder_discovery(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text(
        "from data_joinery import Job, Pipeline\n"
        "def build_job():\n    return Job(pipeline=Pipeline())\n"
    )
    monkeypatch.chdir(tmp_path)

    assert CliRunner().invoke(app, ["run"]).exit_code == 0


def test_explicit_file_builder(pipeline_file: Path, tmp_path: Path):
    destination = tmp_path / "built.txt"

    CliRunner().invoke(app, ["run", f"{pipeline_file}:build_job", str(destination)])

    assert destination.read_text() == "produce,publish"


def test_direct_script(pipeline_file: Path, tmp_path: Path):
    import subprocess
    import sys

    destination = tmp_path / "direct.txt"

    subprocess.run(
        [sys.executable, str(pipeline_file), "run", str(destination)], check=True
    )

    assert destination.read_text() == "produce,publish"


def test_visualization_optional_dependency_error(pipeline_file: Path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ImportError("Pipeline visualization requires matplotlib")

    monkeypatch.setattr(Pipeline, "visualize", unavailable)

    result = CliRunner().invoke(app, ["visualize", str(pipeline_file)])

    assert "requires matplotlib" in result.output
    assert result.exit_code != 0


def test_saved_figure_is_closed(pipeline_file: Path, tmp_path: Path):
    pyplot = pytest.importorskip("matplotlib.pyplot")
    before = pyplot.get_fignums()

    CliRunner().invoke(
        app, ["visualize", str(pipeline_file), "--output", str(tmp_path / "report.svg")]
    )

    assert pyplot.get_fignums() == before
