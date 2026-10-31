from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any
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
    job = Job(pipeline=pipeline)

    @job.context()
    def context(destination: Path, count: int = 2) -> RunContext:
        return RunContext(destination, count)

    CliRunner().invoke(job.app, ["run", "report.csv", "--count", "4"])

    execute.assert_called_once_with(
        RunContext(Path("report.csv"), 4), include_side_effects=True
    )


def test_provider_keeps_identity():
    job = Job(pipeline=Pipeline(RunContext))

    def provider() -> RunContext:
        return RunContext(Path("report.csv"))

    registered = job.context()(provider)

    assert registered is provider


def test_typed_options_and_keyword_only_defaults(monkeypatch):
    pipeline = Pipeline(RunContext)
    execute = Mock()
    monkeypatch.setattr(pipeline, "run", execute)
    job = Job(pipeline=pipeline)

    @job.context()
    def context(
        destination: Annotated[Path, typer.Option("--destination", "-d")],
        *,
        environment: Annotated[Environment, typer.Option()] = Environment.PREPROD,
        count: int = 2,
    ) -> RunContext:
        return RunContext(destination / environment.value, count)

    CliRunner().invoke(job.app, ["run", "-d", "reports", "--environment", "prod"])

    execute.assert_called_once_with(
        RunContext(Path("reports/prod")), include_side_effects=True
    )


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
    job = Job(pipeline=Pipeline(RunContext))
    acquired = Mock()

    @job.context()
    def context(destination: Path, count: int = 2) -> RunContext:
        acquired()
        return RunContext(destination, count)

    CliRunner().invoke(job.app, arguments)

    acquired.assert_not_called()


def test_help_preserves_metadata_and_enum_choices():
    job = Job(pipeline=Pipeline(RunContext))

    @job.context()
    def context(
        environment: Annotated[
            Environment, typer.Option(help="Deployment environment.")
        ],
    ) -> RunContext:
        return RunContext(Path(environment.value))

    result = CliRunner().invoke(job.app, ["run", "--help"])

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
    job = Job(pipeline=pipeline)

    @job.context()
    @contextmanager
    def context():
        events.append("enter")
        try:
            yield RunContext(Path("report.csv"))
        finally:
            events.append("exit")

    def execute(*args, **kwargs):
        events.append("execute")
        if failure is not None:
            raise failure

    monkeypatch.setattr(pipeline, "run", execute)
    CliRunner().invoke(job.app, ["run", "--skip-side-effects"])

    assert events == ["enter", "execute", "exit"]


def test_validation_failure_closes_manager():
    events = []
    job = Job(pipeline=Pipeline(RunContext))

    @job.context()
    @contextmanager
    def context():
        try:
            yield "wrong type"
        finally:
            events.append("closed")

    result = CliRunner().invoke(job.app, ["run"])

    assert isinstance(result.exception, TypeError)
    assert events == ["closed"]


@pytest.mark.parametrize("suppress", [False, True])
def test_manager_cannot_suppress_pipeline_failure(monkeypatch, suppress):
    pipeline = Pipeline(RunContext)
    job = Job(pipeline=pipeline)
    failure = RuntimeError("execution failed")
    monkeypatch.setattr(pipeline, "run", Mock(side_effect=failure))

    class Manager:
        def __enter__(self):
            return RunContext(Path("report.csv"))

        def __exit__(self, *args):
            return suppress

    @job.context()
    def context():
        return Manager()

    result = CliRunner().invoke(job.app, ["run"])

    assert result.exception is failure
    assert "Pipeline finished." not in result.output


def test_cleanup_failure_chains_execution_failure(monkeypatch):
    pipeline = Pipeline(RunContext)
    job = Job(pipeline=pipeline)
    failure = RuntimeError("execution failed")
    monkeypatch.setattr(pipeline, "run", Mock(side_effect=failure))

    @job.context()
    @contextmanager
    def context():
        try:
            yield RunContext(Path("report.csv"))
        finally:
            raise ValueError("cleanup failed")

    result = CliRunner().invoke(job.app, ["run"])

    assert result.exception is not None
    assert result.exception.__context__ is failure


def test_cleanup_failure_prevents_completion():
    job = Job(pipeline=Pipeline(RunContext))

    @job.context()
    @contextmanager
    def context():
        yield RunContext(Path("report.csv"))
        raise RuntimeError("cleanup failed")

    result = CliRunner().invoke(job.app, ["run"])

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

    job = Job(pipeline=Pipeline(ManagedContext))

    @job.context()
    def context():
        return ManagedContext(1)

    assert CliRunner().invoke(job.app, ["run"]).exit_code == 0


@pytest.mark.parametrize(
    "declaration",
    [
        "skip_side_effects: bool = False",
        "value: Annotated[str, typer.Option('--skip-side-effects')] = ''",
        "value: Annotated[bool, typer.Option('--enabled/--skip-side-effects')] = False",
        "value: str = typer.Option('', '--help')",
        "*args",
        "**kwargs",
        "value, /",
        "value: Annotated[str, typer.Option('--help')] = ''",
    ],
)
def test_invalid_parameters_identify_offender(declaration):
    namespace: dict[str, Any] = {"Annotated": Annotated, "typer": typer}
    exec(f"def provider({declaration}): pass", namespace)  # noqa: S102 - test signatures
    job = Job(pipeline=Pipeline(RunContext))

    with pytest.raises((ValueError, TypeError), match="provider.*parameter"):
        job.context()(namespace["provider"])


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
    with pytest.raises(TypeError, match="Provider"):
        Job(pipeline=Pipeline(RunContext)).context()(provider)


def test_duplicate_registration_rejected():
    job = Job(pipeline=Pipeline(RunContext))
    job.context()(lambda: RunContext(Path("x")))

    with pytest.raises(ValueError, match="already registered"):
        job.context()(lambda: RunContext(Path("x")))


def test_late_registration_rejected():
    job = Job(pipeline=Pipeline(RunContext))
    _ = job.app

    with pytest.raises(ValueError, match="finalized"):
        job.context()(lambda: RunContext(Path("x")))


def test_context_free_job_rejects_provider():
    with pytest.raises(TypeError, match="context-free"):
        Job(pipeline=Pipeline()).context()(lambda: None)


def test_context_free_job_runs():
    assert CliRunner().invoke(Job(pipeline=Pipeline()).app, ["run"]).exit_code == 0


def test_missing_provider_fails_run():
    result = CliRunner().invoke(Job(pipeline=Pipeline(RunContext)).app, ["run"])

    assert isinstance(result.exception, TypeError)


def test_missing_provider_allows_help():
    result = CliRunner().invoke(
        Job(pipeline=Pipeline(RunContext)).app, ["run", "--help"]
    )

    assert result.exit_code == 0


def test_missing_provider_allows_visualization(monkeypatch):
    pipeline = Pipeline(RunContext)
    visualize = Mock()
    monkeypatch.setattr(pipeline, "visualize", visualize)

    CliRunner().invoke(Job(pipeline=pipeline).app, ["visualize"])

    visualize.assert_called_once_with(show=True)


def test_visualization_does_not_acquire_provider(monkeypatch):
    pipeline = Pipeline(RunContext)
    monkeypatch.setattr(pipeline, "visualize", Mock())
    job = Job(pipeline=pipeline)
    provider = Mock()

    @job.context()
    def context():
        provider()
        return RunContext(Path("x"))

    CliRunner().invoke(job.app, ["visualize"])

    provider.assert_not_called()


def test_invalid_enum_never_invokes_provider():
    job = Job(pipeline=Pipeline(RunContext))
    acquired = Mock()

    @job.context()
    def context(environment: Annotated[Environment, typer.Option()]):
        acquired()
        return RunContext(Path(environment.value))

    CliRunner().invoke(job.app, ["run", "--environment", "unknown"])

    acquired.assert_not_called()


@pytest.mark.parametrize("skip", [False, True])
def test_managed_run_side_effects(skip):
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
    job = Job(pipeline=pipeline)

    @job.context()
    @contextmanager
    def context():
        events.append("enter")
        try:
            yield RunContext(Path("report.csv"))
        finally:
            events.append("exit")

    CliRunner().invoke(job.app, ["run", *(["--skip-side-effects"] if skip else [])])

    expected = (
        ["enter", "produce", "exit"]
        if skip
        else ["enter", "produce", "publish", "exit"]
    )
    assert events == expected


def test_provider_input_validation():
    job = Job(pipeline=Pipeline(RunContext))

    @job.context()
    def context():
        raise typer.BadParameter("Invalid deployment configuration")

    result = CliRunner().invoke(job.app, ["run"])

    assert result.exit_code == 2


def test_plain_provider_wrong_context_type():
    job = Job(pipeline=Pipeline(RunContext))

    @job.context()
    def context():
        return "wrong"

    result = CliRunner().invoke(job.app, ["run"])

    assert "expected context of type RunContext" in str(result.exception)
