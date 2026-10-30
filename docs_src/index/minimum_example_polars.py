from datetime import UTC, date, datetime
from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Pipeline, Schema, Strict, transform


class Orders(JoineryModel):
    order_timestamp: Column[datetime]
    customer_id: Column[str]
    order_value: Column[float]


class OrderMetrics(JoineryModel):
    order_date: Column[date]
    customer_id: Column[str]
    total_order_value: Column[float]


@transform
def read_orders() -> Annotated[pl.LazyFrame, Strict(Orders)]:
    return Schema(Orders).create_dataframe(
        [
            Orders(
                order_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                customer_id="customer_1",
                order_value=10.0,
            ),
            Orders(
                order_timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                customer_id="customer_2",
                order_value=20.0,
            ),
            Orders(
                order_timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                customer_id="customer_2",
                order_value=30.0,
            ),
        ],
        pl.LazyFrame,
    )


@transform
def get_metrics(
    order_table: Annotated[pl.LazyFrame, Strict(Orders)],
) -> Annotated[pl.LazyFrame, Strict(OrderMetrics)]:
    return order_table.group_by(
        pl.col(Orders.order_timestamp).dt.date().alias(OrderMetrics.order_date),
        Orders.customer_id,
    ).agg(pl.col(Orders.order_value).sum().alias(OrderMetrics.total_order_value))


@transform(side_effect=True)
def print_metrics(metrics_table: Annotated[pl.LazyFrame, Strict(OrderMetrics)]) -> None:
    print(metrics_table.sort(OrderMetrics.customer_id).collect())


order_metrics = Pipeline()
read_orders_step = order_metrics.add_step(read_orders)
get_metrics_step = order_metrics.add_step(get_metrics)
print_metrics_step = order_metrics.add_step(print_metrics)
read_orders_step >> get_metrics_step >> print_metrics_step
order_metrics.run()
