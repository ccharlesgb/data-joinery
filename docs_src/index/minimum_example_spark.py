from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import DoubleType, StructType

from data_joinery import Context, Pipeline, Schema, Strict, transform
from data_joinery.backends.spark import SparkContext


@dataclass
class Orders:
    order_timestamp: datetime
    customer_id: str
    order_value: float


@dataclass
class OrderMetrics:
    order_date: date
    customer_id: str
    total_order_value: Annotated[float, DoubleType()]


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
    return (
        order_table.groupBy(
            order_table["order_timestamp"].cast("date").alias("order_date"),
            order_table["customer_id"],
        )
        .sum("order_value")
        .withColumnRenamed("sum(order_value)", "total_order_value")
    )


@transform
def print_metrics(metrics_table: Annotated[DataFrame, Strict(OrderMetrics)]) -> None:
    metrics_table.orderBy("customer_id").show()


order_metrics = Pipeline(SparkContext)
read_orders_step = order_metrics.add_step(read_orders)
get_metrics_step = order_metrics.add_step(get_metrics)
print_metrics_step = order_metrics.add_step(print_metrics)

read_orders_step >> get_metrics_step >> print_metrics_step

spark = SparkSession.builder.config("spark.sql.session.timeZone", "UTC").getOrCreate()

order_metrics.run(SparkContext(spark))
