"""Render representative pipeline shapes for visual review.

Run: uv run --extra vis python scripts/render_pipeline_gallery.py
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import matplotlib
import polars as pl

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from data_joinery import Pipeline, Strict, transform


class Records: ...


class Features: ...


class Summary: ...


@transform
def read_records() -> Records:
    return Records()


@transform
def clean_records(records: Records) -> Records:
    return records


@transform
def enrich_records(records: Records) -> Records:
    return records


@transform
def combine_records(primary: Records, secondary: Records) -> Records:
    return primary


@transform
def build_features(records: Records) -> Features:
    return Features()


@transform
def train_model(features: Features) -> Summary:
    return Summary()


@transform
def evaluate_model(features: Features, summary: Summary) -> Summary:
    return summary


@transform
def publish_report(summary: Summary) -> None:
    return None


def small() -> Pipeline:
    pipeline = Pipeline()
    source = pipeline.add_step(read_records, "raw records")
    features = pipeline.add_step(build_features, "build features")
    model = pipeline.add_step(train_model, "fit model")
    pipeline.connect(source, features)
    pipeline.connect(features, model)
    return pipeline


def branching() -> Pipeline:
    pipeline = Pipeline()
    raw = pipeline.add_step(read_records, "raw records")
    clean = pipeline.add_step(clean_records, "clean records")
    enrich = pipeline.add_step(enrich_records, "enrich records")
    combined = pipeline.add_step(combine_records, "combine records")
    features = pipeline.add_step(build_features, "feature table")
    model = pipeline.add_step(train_model, "fit model")
    evaluation = pipeline.add_step(evaluate_model, "evaluate model")
    report = pipeline.add_step(publish_report, "publish report")
    pipeline.connect(raw, clean)
    pipeline.connect(raw, enrich)
    pipeline.connect(clean, combined, param="primary")
    pipeline.connect(enrich, combined, param="secondary")
    pipeline.connect(combined, features)
    pipeline.connect(features, model)
    pipeline.connect(features, evaluation, param="features")
    pipeline.connect(model, evaluation, param="summary")
    pipeline.connect(evaluation, report)
    return pipeline


def large() -> Pipeline:
    pipeline = Pipeline()
    sources = [pipeline.add_step(read_records, f"source {i + 1}") for i in range(5)]
    for i, source in enumerate(sources):
        clean = pipeline.add_step(clean_records, f"clean source {i + 1}")
        features = pipeline.add_step(build_features, f"features {i + 1}")
        model = pipeline.add_step(train_model, f"model {i + 1}")
        evaluation = pipeline.add_step(evaluate_model, f"evaluate {i + 1}")
        report = pipeline.add_step(publish_report, f"publish {i + 1}")
        pipeline.connect(source, clean)
        pipeline.connect(clean, features)
        pipeline.connect(features, model)
        pipeline.connect(features, evaluation, param="features")
        pipeline.connect(model, evaluation, param="summary")
        pipeline.connect(evaluation, report)
    return pipeline


@dataclass
class Orders:
    order_id: int
    amount: float


@transform
def read_orders() -> Annotated[pl.DataFrame, Strict(Orders)]:
    return pl.DataFrame({"order_id": [1], "amount": [10.0]})


@transform
def filter_orders(
    orders: Annotated[pl.DataFrame, Strict(Orders)],
) -> Annotated[pl.DataFrame, Strict(Orders)]:
    return orders


def dataframe() -> Pipeline:
    pipeline = Pipeline()
    source = pipeline.add_step(read_orders, "read orders")
    filtered = pipeline.add_step(filter_orders, "filter orders")
    pipeline.connect(source, filtered)
    return pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "scratch"
        / "pipeline-visualisation",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, build in (
        ("small", small),
        ("branching", branching),
        ("large", large),
        ("dataframe", dataframe),
    ):
        figure = build().visualize(show=False)
        path = args.output_dir / f"{name}.png"
        figure.savefig(path, dpi=150, facecolor=figure.get_facecolor())
        figure.savefig(path.with_suffix(".svg"), facecolor=figure.get_facecolor())
        plt.close(figure)
        print(path)


if __name__ == "__main__":
    main()
