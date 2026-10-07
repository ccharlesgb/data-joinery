import traceback
from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame

from data_joinery import Pipeline, Strict, transform
from data_joinery.pipeline import PipelineCycleError


@dataclass
class A: ...


@dataclass
class B: ...


@transform
def transform_data(
    _: Annotated[DataFrame, Strict(A)],
) -> Annotated[DataFrame, Strict(B)]: ...


@transform
def transform_data_back(
    _: Annotated[DataFrame, Strict(B)],
) -> Annotated[DataFrame, Strict(A)]: ...


order_metrics = Pipeline()
transform_data_step = order_metrics.add_step(transform_data)
transform_data_back_step = order_metrics.add_step(transform_data_back)

order_metrics.connect(transform_data_step, transform_data_back_step)
try:
    order_metrics.connect(transform_data_back_step, transform_data_step)
except PipelineCycleError:
    print(traceback.format_exc(limit=1))
