from dataclasses import dataclass
from datetime import date
from typing import Annotated

import typer
from typer.testing import CliRunner

from data_joinery import Context, Job, Pipeline, side_effect, transform


class RunDate(date):
    """Distinguish the report date from other dates in the context."""


@dataclass(frozen=True)
class PipelineContext:
    """Dependencies supplied to the report steps."""

    run_date: RunDate


@transform
def make_report(run_date: Annotated[RunDate, Context()]) -> str:
    """Create a report for the supplied date."""
    return f"Report for {run_date.isoformat()}"


@side_effect
def print_report(report: str) -> None:
    """Publish the report to standard output."""
    print(report)


def build_pipeline() -> Pipeline[PipelineContext]:
    """Build the graph without acquiring runtime resources."""
    pipeline = Pipeline(PipelineContext)
    pipeline.add_step(make_report) >> pipeline.add_step(print_report)
    return pipeline


job = Job(pipeline=build_pipeline())


@job.context()
def context(
    run_date: Annotated[str, typer.Argument(help="Report date in YYYY-MM-DD format.")],
) -> PipelineContext:
    """Prepare the report dependencies."""
    try:
        return PipelineContext(run_date=RunDate.fromisoformat(run_date))
    except ValueError as error:
        raise typer.BadParameter("Use a date in YYYY-MM-DD format.") from error


if __name__ == "__main__":
    result = CliRunner().invoke(job.app, ["run", "2026-10-11"])
    if result.exception is not None:
        raise result.exception
    print(result.output, end="")
