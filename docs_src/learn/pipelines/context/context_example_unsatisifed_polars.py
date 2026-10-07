import traceback
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
    run_date: date


@transform
def read_data(
    run_date: Annotated[RunDate, Context()],
) -> Annotated[pl.DataFrame, Strict(A)]:
    expected_path = Path(__file__).parent / f"example_{run_date.strftime('%Y%m%d')}.csv"
    return pl.read_csv(expected_path)


@transform
def write_data(b: Annotated[pl.DataFrame, Strict(A)]) -> None:
    print(b)


try:
    order_metrics = Pipeline(PipelineDependencies)
    order_metrics.add_step(read_data)
except TypeError:
    print(traceback.format_exc(limit=1))
