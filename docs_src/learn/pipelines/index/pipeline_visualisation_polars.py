"""A branch and join pipeline for the data flow figure."""

from dataclasses import dataclass
from typing import Annotated, cast

import polars as pl

from data_joinery import Pipeline, Strict, transform


@dataclass
class Orders:
    order_id: int
    amount: float


@dataclass
class ScoredOrders:
    order_id: int
    amount: float
    score: float


@dataclass
class ScoreModel:
    threshold: float


@transform
def read_orders() -> Annotated[pl.DataFrame, Strict(Orders)]:
    return pl.DataFrame({"order_id": [1, 2], "amount": [50.0, 150.0]})


@transform
def clean_orders(
    orders: Annotated[pl.DataFrame, Strict(Orders)],
) -> Annotated[pl.DataFrame, Strict(Orders)]:
    return orders.filter(pl.col("amount") >= 0)


@transform
def priority_orders(
    orders: Annotated[pl.DataFrame, Strict(Orders)],
) -> Annotated[pl.DataFrame, Strict(Orders)]:
    return orders.filter(pl.col("amount") > 100)


@transform
def combine_orders(
    cleaned: Annotated[pl.DataFrame, Strict(Orders)],
    priority: Annotated[pl.DataFrame, Strict(Orders)],
) -> Annotated[pl.DataFrame, Strict(Orders)]:
    return pl.concat([cleaned, priority]).unique(
        subset=["order_id"], maintain_order=True
    )


@transform
def fit_threshold(
    orders: Annotated[pl.DataFrame, Strict(Orders)],
) -> ScoreModel:
    mean = cast(float | None, orders["amount"].mean())
    if mean is None:
        raise ValueError("cannot fit a threshold from empty orders")
    return ScoreModel(threshold=mean)


@transform
def score_orders(
    orders: Annotated[pl.DataFrame, Strict(Orders)],
    model: ScoreModel,
) -> Annotated[pl.DataFrame, Strict(ScoredOrders)]:
    return orders.with_columns((pl.col("amount") / model.threshold).alias("score"))


@transform
def write_scores(
    scores: Annotated[pl.DataFrame, Strict(ScoredOrders)],
) -> None:
    print(scores)


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
