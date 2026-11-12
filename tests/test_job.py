from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, cast
from unittest.mock import Mock

import pytest
import typer
from typer.testing import CliRunner

from data_joinery import Job, Pipeline


@dataclass(frozen=True)
class RunContext:
    destination: Path
    count: int = 2


class Environment(StrEnum):
    PREPROD = "preprod"
    PROD = "prod"


def test_plain_provider_passes_complete_context(monkeypatch):
    pipeline = Pipeline(RunContext)
    execute = Mock()
    monkeypatch.setattr(pipeline, "run", execute)

    def context(destination: Path, count: int = 2) -> RunContext:
        return RunContext(destination, count)

    job = Job(pipeline=pipeline, context_provider=context)

    CliRunner().invoke(job, ["run", "report.csv", "--count", "4"])

    execute.assert_called_once_with(RunContext(Path("report.csv"), 4))


def test_typed_options_and_keyword_only_defaults(monkeypatch):
    pipeline = Pipeline(RunContext)
    execute = Mock()
    monkeypatch.setattr(pipeline, "run", execute)

    def context(
        destination: Annotated[Path, typer.Option("--destination", "-d")],
        *,
        environment: Annotated[Environment, typer.Option()] = Environment.PREPROD,
        count: int = 2,
    ) -> RunContext:
        return RunContext(destination / environment.value, count)

    job = Job(pipeline=pipeline, context_provider=context)

    CliRunner().invoke(job, ["run", "-d", "reports", "--environment", "prod"])

    execute.assert_called_once_with(RunContext(Path("reports/prod")))


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--help"],
        ["run", "--help"],
        ["run"],
        ["run", "x", "--count", "bad"],
        ["run", "x", "--unknown"],
    ],
)
def test_help_and_invalid_inputs_do_not_acquire(arguments):
    acquired = Mock()

    def context(destination: Path, count: int = 2) -> RunContext:
        acquired()
        return RunContext(destination, count)

    job = Job(pipeline=Pipeline(RunContext), context_provider=context)

    CliRunner().invoke(job, arguments)

    acquired.assert_not_called()


def test_help_preserves_metadata_and_enum_choices():
    def context(
        environment: Annotated[
            Environment, typer.Option(help="Deployment environment.")
        ],
    ) -> RunContext:
        return RunContext(Path(environment.value))

    job = Job(pipeline=Pipeline(RunContext), context_provider=context)

    result = CliRunner().invoke(job, ["run", "--help"])

    assert all(
        text in result.output for text in ["Deployment environment.", "preprod", "prod"]
    )


@pytest.mark.parametrize(
    "failure",
    [
        None,
        RuntimeError("execution failed"),
        KeyboardInterrupt(),
        TypeError("invalid context"),
    ],
)
def test_managed_provider_lifecycle(monkeypatch, failure):
    events = []
    pipeline = Pipeline(RunContext)

    @contextmanager
    def context():
        events.append("enter")
        try:
            yield RunContext(Path("report.csv"))
        finally:
            events.append("exit")

    job = Job(pipeline=pipeline, context_provider=context)

    def execute(*args, **kwargs):
        events.append("execute")
        if failure is not None:
            raise failure

    monkeypatch.setattr(pipeline, "run", execute)
    CliRunner().invoke(job, ["run"])

    assert events == ["enter", "execute", "exit"]


def test_validation_failure_closes_manager():
    events = []

    @contextmanager
    def context():
        try:
            yield "wrong type"
        finally:
            events.append("closed")

    job = Job(pipeline=Pipeline(RunContext), context_provider=cast(Any, context))

    result = CliRunner().invoke(job, ["run"])

    assert isinstance(result.exception, TypeError)
    assert events == ["closed"]


@pytest.mark.parametrize("suppress", [False, True])
def test_manager_cannot_suppress_pipeline_failure(monkeypatch, suppress):
    pipeline = Pipeline(RunContext)
    failure = RuntimeError("execution failed")
    monkeypatch.setattr(pipeline, "run", Mock(side_effect=failure))

    class Manager:
        def __enter__(self):
            return RunContext(Path("report.csv"))

        def __exit__(self, *args):
            return suppress

    def context():
        return Manager()

    job = Job(pipeline=pipeline, context_provider=context)

    result = CliRunner().invoke(job, ["run"])

    assert result.exception is failure
    assert "Pipeline finished." not in result.output


def test_cleanup_failure_chains_execution_failure(monkeypatch):
    pipeline = Pipeline(RunContext)
    failure = RuntimeError("execution failed")
    monkeypatch.setattr(pipeline, "run", Mock(side_effect=failure))

    @contextmanager
    def context():
        try:
            yield RunContext(Path("report.csv"))
        finally:
            raise ValueError("cleanup failed")

    job = Job(pipeline=pipeline, context_provider=context)

    result = CliRunner().invoke(job, ["run"])

    assert result.exception is not None
    assert result.exception.__context__ is failure


def test_cleanup_failure_prevents_completion():
    @contextmanager
    def context():
        yield RunContext(Path("report.csv"))
        raise RuntimeError("cleanup failed")

    job = Job(pipeline=Pipeline(RunContext), context_provider=context)

    result = CliRunner().invoke(job, ["run"])

    assert isinstance(result.exception, RuntimeError)
    assert "Pipeline finished." not in result.output


def test_context_instance_is_not_entered():
    @dataclass
    class ManagedContext:
        value: int

        def __enter__(self):
            raise AssertionError("Must not enter the context instance")

        def __exit__(self, *args):
            raise AssertionError("Must not close the context instance")

    def context():
        return ManagedContext(1)

    job = Job(pipeline=Pipeline(ManagedContext), context_provider=context)

    assert CliRunner().invoke(job, ["run"]).exit_code == 0


@pytest.mark.parametrize("kind", ["async", "generator", "async_generator"])
def test_unsupported_provider_kinds(kind):
    async def async_provider():
        pass

    def generator():
        yield RunContext(Path("x"))

    async def async_generator():
        yield RunContext(Path("x"))

    provider = {
        "async": async_provider,
        "generator": generator,
        "async_generator": async_generator,
    }[kind]
    with pytest.raises(TypeError, match="providers"):
        Job(pipeline=Pipeline(RunContext), context_provider=cast(Any, provider))


def test_context_free_job_rejects_provider():
    with pytest.raises(TypeError, match="context-free"):
        Job(pipeline=Pipeline(), context_provider=lambda: None)


def test_context_free_job_runs():
    assert CliRunner().invoke(Job(pipeline=Pipeline()), ["run"]).exit_code == 0


def test_missing_provider_fails_construction():
    with pytest.raises(TypeError, match="requires a context_provider passed to Job"):
        Job(pipeline=Pipeline(RunContext))


def test_visualization_does_not_acquire_provider(monkeypatch):
    pipeline = Pipeline(RunContext)
    monkeypatch.setattr(pipeline, "visualize", Mock())
    provider = Mock()

    def context():
        provider()
        return RunContext(Path("x"))

    job = Job(pipeline=pipeline, context_provider=context)

    CliRunner().invoke(job, ["visualize"])

    provider.assert_not_called()


def test_invalid_enum_never_invokes_provider():
    acquired = Mock()

    def context(environment: Annotated[Environment, typer.Option()]):
        acquired()
        return RunContext(Path(environment.value))

    job = Job(pipeline=Pipeline(RunContext), context_provider=context)

    CliRunner().invoke(job, ["run", "--environment", "unknown"])

    acquired.assert_not_called()


def test_managed_run_side_effects():
    from data_joinery import side_effect, transform

    events = []

    @transform
    def produce() -> str:
        events.append("produce")
        return "report"

    @side_effect
    def publish(report: str) -> None:
        events.append("publish")

    pipeline = Pipeline(RunContext)
    pipeline.add_step(produce) >> pipeline.add_step(publish)

    @contextmanager
    def context():
        events.append("enter")
        try:
            yield RunContext(Path("report.csv"))
        finally:
            events.append("exit")

    job = Job(pipeline=pipeline, context_provider=context)

    CliRunner().invoke(job, ["run"])

    expected = ["enter", "produce", "publish", "exit"]
    assert events == expected


def test_provider_input_validation():
    def context():
        raise typer.BadParameter("Invalid deployment configuration")

    job = Job(pipeline=Pipeline(RunContext), context_provider=context)

    result = CliRunner().invoke(job, ["run"])

    assert result.exit_code == 2


def test_plain_provider_wrong_context_type():
    def context():
        return "wrong"

    job = Job(pipeline=Pipeline(RunContext), context_provider=cast(Any, context))

    result = CliRunner().invoke(job, ["run"])

    assert "expected context of type RunContext" in str(result.exception)


@pytest.mark.parametrize("name", ["destination", "inputs", "kwargs"])
@pytest.mark.parametrize("postponed", [False, True])
@pytest.mark.parametrize("managed", [False, True])
def test_provider_annotations_from_another_module(
    monkeypatch, name, postponed, managed
):
    namespace: dict[str, Any] = {"RunContext": RunContext}
    future = "from __future__ import annotations\n" if postponed else ""
    decorator = "@contextmanager\n" if managed else ""
    body = "yield" if managed else "return"
    exec(  # noqa: S102 - exercise provider globals and postponed annotations
        future
        + "from contextlib import contextmanager\n"
        + "from pathlib import Path\n"
        + "from typing import Annotated\n"
        + "import typer\n"
        + decorator
        + f"def provider({name}: Annotated[Path, typer.Option(help='Report destination.')]):\n"
        + '    """Generate the report."""\n'
        + f"    {body} RunContext({name})\n",
        namespace,
    )
    pipeline = Pipeline(RunContext)
    execute = Mock()
    monkeypatch.setattr(pipeline, "run", execute)
    job = Job(pipeline=pipeline, context_provider=namespace["provider"])

    CliRunner().invoke(job, ["run", f"--{name}", "report.csv"])

    execute.assert_called_once_with(RunContext(Path("report.csv")))


def test_run_help_uses_command_description():
    def generate_report() -> RunContext:
        """Generate the daily report."""
        return RunContext(Path("report.csv"))

    job = Job(pipeline=Pipeline(RunContext), context_provider=generate_report)

    assert "Run the pipeline." in CliRunner().invoke(job, ["run", "--help"]).output


def test_provider_can_define_skip_side_effects_option(monkeypatch):
    pipeline = Pipeline(RunContext)
    execute = Mock()
    monkeypatch.setattr(pipeline, "run", execute)

    def context(skip_side_effects: bool = False) -> RunContext:
        return RunContext(Path("report.csv"), int(skip_side_effects))

    job = Job(pipeline=pipeline, context_provider=context)
    CliRunner().invoke(job, ["run", "--skip-side-effects"])

    execute.assert_called_once_with(RunContext(Path("report.csv"), 1))


def test_additional_typer_command():
    job = Job(pipeline=Pipeline())

    @job.command()
    def status() -> None:
        """Show application status."""
        typer.echo("Ready")

    assert CliRunner().invoke(job, ["status"]).output == "Ready\n"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--skip-side-effects", "run"],
        ["--skip-side-effects", "visualize"],
        ["run", "--skip-side-effects"],
        ["visualize", "--skip-side-effects"],
    ],
)
def test_job_rejects_skip_side_effects_option(arguments):
    job = Job(pipeline=Pipeline())

    result = CliRunner().invoke(job, arguments)

    assert result.exit_code == 2
