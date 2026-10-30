from datetime import UTC, date, datetime
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StructType

from data_joinery import (
    Column,
    Context,
    JoineryModel,
    Pipeline,
    Schema,
    Strict,
    transform,
)
from data_joinery.backends.spark import SparkContext


class Orders(JoineryModel):
    order_timestamp: Column[datetime]
    customer_id: Column[str]
    order_value: Column[float]


class OrderMetrics(JoineryModel):
    order_date: Column[date]
    customer_id: Column[str]
    total_order_value: Column[Annotated[float, DoubleType()]]


@transform
def read_orders(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Strict(Orders)]:
    input_schema = Schema(Orders).native_schema(StructType)
    return spark.createDataFrame(
        [
            (datetime(2026, 1, 1, tzinfo=UTC), "customer_1", 10.0),
            (datetime(2026, 1, 2, tzinfo=UTC), "customer_2", 20.0),
            (datetime(2026, 1, 2, tzinfo=UTC), "customer_2", 30.0),
        ],
        schema=input_schema,
    )


@transform
def get_metrics(
    order_table: Annotated[DataFrame, Strict(Orders)],
) -> Annotated[DataFrame, Strict(OrderMetrics)]:
    return order_table.groupBy(
        F.col(Orders.order_timestamp).cast("date").alias(OrderMetrics.order_date),
        Orders.customer_id,
    ).agg(F.sum(Orders.order_value).alias(OrderMetrics.total_order_value))


@transform(side_effect=True)
def print_metrics(metrics_table: Annotated[DataFrame, Strict(OrderMetrics)]) -> None:
    metrics_table.orderBy(OrderMetrics.customer_id).show()


order_metrics = Pipeline(SparkContext)
read_orders_step = order_metrics.add_step(read_orders)
get_metrics_step = order_metrics.add_step(get_metrics)
print_metrics_step = order_metrics.add_step(print_metrics)

read_orders_step >> get_metrics_step >> print_metrics_step

spark = SparkSession.builder.config("spark.sql.session.timeZone", "UTC").getOrCreate()

order_metrics.run(SparkContext(spark))
