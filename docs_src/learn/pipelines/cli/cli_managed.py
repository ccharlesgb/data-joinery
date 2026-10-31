from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import typer
from typer.testing import CliRunner

from data_joinery import Context, Job, Pipeline, side_effect, transform


class Environment(StrEnum):
    """Deployment choices for this report."""

    PREPROD = "preprod"
    PROD = "prod"


@dataclass(frozen=True)
class ReportContext:
    """Workspace and deployment dependencies for report steps."""

    destination: Path
    environment: Environment


@transform
def make_report(environment: Annotated[Environment, Context()]) -> str:
    """Create a report for the selected environment."""
    return f"Report for {environment.value}"


@side_effect
def write_report(report: str, destination: Annotated[Path, Context()]) -> None:
    """Write the report to the temporary workspace."""
    destination.write_text(report)
    print(report)


pipeline = Pipeline(ReportContext)
pipeline.add_step(make_report) >> pipeline.add_step(write_report)
job = Job(pipeline=pipeline)


@job.context()
@contextmanager
def context(
    environment: Annotated[
        Environment, typer.Option(help="Environment to run against.")
    ] = Environment.PREPROD,
) -> Generator[ReportContext]:
    """Create a temporary workspace and remove it after execution."""
    with TemporaryDirectory() as directory:
        print("Workspace acquired.")
        try:
            yield ReportContext(Path(directory) / "report.txt", environment)
        finally:
            print("Releasing workspace.")


if __name__ == "__main__":
    result = CliRunner().invoke(job.app, ["run", "--environment", "preprod"])
    if result.exception is not None:
        raise result.exception
    print(result.output, end="")
