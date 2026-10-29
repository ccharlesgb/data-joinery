import traceback
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, PipelineExecutionError, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


class A(JoineryModel):
    a: Column[str]


class B(JoineryModel):
    b: Column[str]


@transform
def transform_data(
    a: Annotated[pl.LazyFrame, Strict(A)],
) -> Annotated[pl.LazyFrame, Strict(B)]:
    return a.rename({A.a: B.b})


@transform
def write_data(
    b: Annotated[pl.LazyFrame, Strict(B)],
) -> None:
    print(b)


order_metrics = Pipeline()
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(transform_data_step, write_data_step)

try:
    order_metrics.run()
except PipelineExecutionError:
    print(traceback.format_exc())
