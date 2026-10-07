from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Schema, Strict, transform


@dataclass
class Orders:
    order_timestamp: datetime
    customer_id: str
    order_value: float


@dataclass
class OrderMetrics:
    order_date: date
    customer_id: str
    total_order_value: float


@transform
def read_orders() -> Annotated[pl.DataFrame, Strict(Orders)]:
    return Schema(Orders).create_dataframe(
        [
            Orders(datetime(2026, 1, 1, tzinfo=UTC), "customer_1", 10.0),
            Orders(datetime(2026, 1, 2, tzinfo=UTC), "customer_2", 20.0),
            Orders(datetime(2026, 1, 2, tzinfo=UTC), "customer_2", 30.0),
        ],
        pl.DataFrame,
    )


@transform
def get_metrics(
    order_table: Annotated[pl.DataFrame, Strict(Orders)],
) -> Annotated[pl.DataFrame, Strict(OrderMetrics)]:
    return order_table.group_by(
        pl.col("order_timestamp").dt.date().alias("order_date"), "customer_id"
    ).agg(pl.col("order_value").sum().alias("total_order_value"))


@transform
def print_metrics(metrics_table: Annotated[pl.DataFrame, Strict(OrderMetrics)]) -> None:
    print(metrics_table.sort("customer_id"))


order_metrics = Pipeline()
read_orders_step = order_metrics.add_step(read_orders)
get_metrics_step = order_metrics.add_step(get_metrics)
print_metrics_step = order_metrics.add_step(print_metrics)
read_orders_step >> get_metrics_step >> print_metrics_step
order_metrics.run()
