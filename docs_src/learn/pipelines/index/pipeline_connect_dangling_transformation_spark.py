import traceback
from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame

from data_joinery import Pipeline, PipelineExecutionError, Strict, transform


@dataclass
class A:
    a: str


@dataclass
class B:
    b: str


@transform
def transform_data(
    a: Annotated[DataFrame, Strict(A)],
) -> Annotated[DataFrame, Strict(B)]:
    return a.withColumnRenamed("a", "b")


@transform
def write_data(
    b: Annotated[DataFrame, Strict(B)],
) -> None:
    b.show()


order_metrics = Pipeline()
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(transform_data_step, write_data_step)

try:
    order_metrics.run()
except PipelineExecutionError:
    print(traceback.format_exc())
