from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Strict, transform


@dataclass
class A:
    a: str


@dataclass
class B:
    b: str


@transform
def read_data() -> Annotated[pl.DataFrame, Strict(A)]:
    return pl.DataFrame({"a": ["value"]})


@transform
def transform_data(
    a: Annotated[pl.DataFrame, Strict(A)],
) -> Annotated[pl.DataFrame, Strict(B)]:
    return a.rename({"a": "b"})


@transform
def write_data(
    b: Annotated[pl.DataFrame, Strict(B)],
) -> None:
    print(b)


order_metrics = Pipeline()
read_data_step = order_metrics.add_step(read_data)
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(read_data_step, transform_data_step)
order_metrics.connect(transform_data_step, write_data_step)

order_metrics.run()
