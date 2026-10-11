from dataclasses import dataclass
from datetime import date
from typing import Annotated

from data_joinery import Context, Pipeline, side_effect, transform


class RunDate(date):
    pass


@dataclass(frozen=True)
class PipelineContext:
    run_date: RunDate

    @classmethod
    def from_kwargs(cls, *, run_date: str) -> "PipelineContext":
        return cls(run_date=RunDate.fromisoformat(run_date))


@transform
def make_report(run_date: Annotated[RunDate, Context()]) -> str:
    return f"Report for {run_date.isoformat()}"


@side_effect
def print_report(report: str) -> None:
    print(report)


def build_pipeline() -> Pipeline[PipelineContext]:
    pipeline = Pipeline(PipelineContext)
    pipeline.add_step(make_report) >> pipeline.add_step(print_report)
    return pipeline


if __name__ == "__main__":
    build_pipeline().run(PipelineContext.from_kwargs(run_date="2026-10-11"))
