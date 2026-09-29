from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Context, Pipeline, Project, transform
from data_joinery.backends.spark import SparkContext
from data_joinery.dbt import Dbt


@dataclass
class Order:
    customer_id: int
    amount: float


@dataclass
class Customer:
    customer_id: int
    name: str


@dataclass
class EnrichedOrder:
    customer_id: int
    amount: float
    name: str


@dataclass(frozen=True)
class PipelineContext(SparkContext):
    dbt: Dbt


@transform
def read_orders(
    dbt: Annotated[Dbt, Context()],
) -> Annotated[DataFrame, Project(Order)]:
    return dbt.ref("upstream_orders")


@transform
def read_customers(
    dbt: Annotated[Dbt, Context()],
) -> Annotated[DataFrame, Project(Customer)]:
    return dbt.source("raw", "customers")


@transform
def enrich_orders(
    orders: Annotated[DataFrame, Project(Order)],
    customers: Annotated[DataFrame, Project(Customer)],
) -> Annotated[DataFrame, Project(EnrichedOrder)]:
    return orders.join(customers, "customer_id").select("customer_id", "amount", "name")


def build_pipeline() -> Pipeline[PipelineContext]:
    pipeline = Pipeline(PipelineContext)

    orders = pipeline.add_step(read_orders)
    customers = pipeline.add_step(read_customers)
    enriched = pipeline.add_step(enrich_orders)

    orders >> enriched
    customers >> enriched

    return pipeline


def model(dbt: Dbt, session: SparkSession) -> DataFrame:
    dbt.config(packages=["data-joinery==0.1.0"])
    outputs = build_pipeline().run(PipelineContext(spark=session, dbt=dbt))
    return outputs["enrich_orders"]
