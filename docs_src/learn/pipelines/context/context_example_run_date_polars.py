from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated

import polars as pl

from data_joinery import Context, Pipeline, Strict, transform


@dataclass
class A:
    snapshot_date: str


class RunDate(date):
    pass


@dataclass(frozen=True)
class PipelineDependencies:
    run_date: RunDate


@transform
def read_data(
    run_date: Annotated[RunDate, Context()],
) -> Annotated[pl.DataFrame, Strict(A)]:
    expected_path = Path(__file__).parent / f"example_{run_date.strftime('%Y%m%d')}.csv"
    return pl.read_csv(expected_path, schema_overrides={"snapshot_date": pl.String})


@transform
def write_data(b: Annotated[pl.DataFrame, Strict(A)]) -> None:
    print(b)


order_metrics = Pipeline(PipelineDependencies)
read_data_step = order_metrics.add_step(read_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(read_data_step, write_data_step)

context = PipelineDependencies(RunDate(2026, 1, 1))

order_metrics.run(context)
