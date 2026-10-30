"""A branch and join pipeline for the data flow figure."""

from dataclasses import dataclass
from typing import Annotated, cast

import polars as pl

from data_joinery import Column, JoineryModel, Pipeline, Strict, transform


class Orders(JoineryModel):
    order_id: Column[int]
    amount: Column[float]


class ScoredOrders(JoineryModel):
    order_id: Column[int]
    amount: Column[float]
    score: Column[float]


@dataclass
class ScoreModel:
    threshold: float


@transform
def read_orders() -> Annotated[pl.LazyFrame, Strict(Orders)]:
    return pl.LazyFrame({Orders.order_id: [1, 2], Orders.amount: [50.0, 150.0]})


@transform
def clean_orders(
    orders: Annotated[pl.LazyFrame, Strict(Orders)],
) -> Annotated[pl.LazyFrame, Strict(Orders)]:
    return orders.filter(pl.col(Orders.amount) >= 0)


@transform
def priority_orders(
    orders: Annotated[pl.LazyFrame, Strict(Orders)],
) -> Annotated[pl.LazyFrame, Strict(Orders)]:
    return orders.filter(pl.col(Orders.amount) > 100)


@transform
def combine_orders(
    cleaned: Annotated[pl.LazyFrame, Strict(Orders)],
    priority: Annotated[pl.LazyFrame, Strict(Orders)],
) -> Annotated[pl.LazyFrame, Strict(Orders)]:
    return pl.concat([cleaned, priority]).unique(
        subset=[Orders.order_id], maintain_order=True
    )


@transform
def fit_threshold(
    orders: Annotated[pl.LazyFrame, Strict(Orders)],
) -> ScoreModel:
    mean = cast(
        float | None, orders.select(pl.col(Orders.amount).mean()).collect().item()
    )
    if mean is None:
        raise ValueError("cannot fit a threshold from empty orders")
    return ScoreModel(threshold=mean)


@transform
def score_orders(
    orders: Annotated[pl.LazyFrame, Strict(Orders)],
    model: ScoreModel,
) -> Annotated[pl.LazyFrame, Strict(ScoredOrders)]:
    return orders.with_columns(
        (pl.col(Orders.amount) / model.threshold).alias(ScoredOrders.score)
    )


@transform(side_effect=True)
def write_scores(
    scores: Annotated[pl.LazyFrame, Strict(ScoredOrders)],
) -> None:
    print(scores.collect())


order_pipeline = Pipeline()
read = order_pipeline.add_step(read_orders, "read orders")
clean = order_pipeline.add_step(clean_orders, "clean orders")
priority = order_pipeline.add_step(priority_orders, "priority orders")
combined = order_pipeline.add_step(combine_orders, "combine orders")
model = order_pipeline.add_step(fit_threshold, "fit threshold")
scored = order_pipeline.add_step(score_orders, "score orders")
written = order_pipeline.add_step(write_scores, "write scores")

order_pipeline.connect(read, clean)
order_pipeline.connect(read, priority)
order_pipeline.connect(clean, combined, param="cleaned")
order_pipeline.connect(priority, combined, param="priority")
order_pipeline.connect(combined, model)
order_pipeline.connect(combined, scored, param="orders")
order_pipeline.connect(model, scored, param="model")
order_pipeline.connect(scored, written)

order_pipeline.run()
