import traceback
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Context, Pipeline, Strict, transform


@dataclass
class A:
    snapshot_date: str


class RunDate(date):
    pass


@dataclass(frozen=True)
class PipelineDependencies:
    spark: SparkSession
    run_date: date


@transform
def read_data(
    spark: Annotated[SparkSession, Context()],
    run_date: Annotated[RunDate, Context()],
) -> Annotated[DataFrame, Strict(A)]:
    expected_path = Path(__file__).parent / f"example_{run_date.strftime('%Y%m%d')}.csv"
    return spark.read.csv(str(expected_path), header=True)


@transform
def write_data(b: Annotated[DataFrame, Strict(A)]) -> None:
    b.show()


try:
    order_metrics = Pipeline(PipelineDependencies)
    order_metrics.add_step(read_data)
except TypeError:
    print(traceback.format_exc(limit=1))
