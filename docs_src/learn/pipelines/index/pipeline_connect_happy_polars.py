from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Pipeline, Strict, transform


class A(JoineryModel):
    a: Column[str]


class B(JoineryModel):
    b: Column[str]


@transform
def read_data() -> Annotated[pl.LazyFrame, Strict(A)]:
    return pl.LazyFrame({A.a: ["value"]})


@transform
def transform_data(
    a: Annotated[pl.LazyFrame, Strict(A)],
) -> Annotated[pl.LazyFrame, Strict(B)]:
    return a.rename({A.a: B.b})


@transform
def write_data(
    b: Annotated[pl.LazyFrame, Strict(B)],
) -> None:
    print(b.collect())


order_metrics = Pipeline()
read_data_step = order_metrics.add_step(read_data)
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(read_data_step, transform_data_step)
order_metrics.connect(transform_data_step, write_data_step)

order_metrics.run()
