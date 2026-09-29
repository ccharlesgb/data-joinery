from dataclasses import dataclass
from typing import Annotated, cast

import polars as pl
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from sklearn.linear_model import LinearRegression

from data_joinery import Context, Pipeline, SparkContext, Strict, transform


@dataclass
class CustomerActivity:
    customer_id: int
    minutes: int
    annual_spend: float


@dataclass
class CustomerFeatures:
    customer_id: int
    visits: int
    total_minutes: int
    annual_spend: float


@transform
def read_activity(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Strict(CustomerActivity)]:
    return spark.createDataFrame(
        [
            CustomerActivity(1, 10, 2_700.0),
            CustomerActivity(1, 20, 2_700.0),
            CustomerActivity(2, 15, 4_000.0),
            CustomerActivity(2, 15, 4_000.0),
            CustomerActivity(2, 20, 4_000.0),
            CustomerActivity(3, 25, 2_000.0),
            CustomerActivity(4, 20, 5_700.0),
            CustomerActivity(4, 20, 5_700.0),
            CustomerActivity(4, 20, 5_700.0),
            CustomerActivity(4, 20, 5_700.0),
            CustomerActivity(5, 20, 3_300.0),
            CustomerActivity(5, 25, 3_300.0),
        ]
    )


@transform
def aggregate_features(
    activity: Annotated[DataFrame, Strict(CustomerActivity)],
) -> Annotated[DataFrame, Strict(CustomerFeatures)]:
    return activity.groupBy("customer_id").agg(
        F.count("*").alias("visits"),
        F.sum("minutes").alias("total_minutes"),
        F.max("annual_spend").alias("annual_spend"),
    )


@transform
def collect_features(
    features: Annotated[DataFrame, Strict(CustomerFeatures)],
) -> Annotated[pl.DataFrame, Strict(CustomerFeatures)]:
    return cast(pl.DataFrame, pl.from_arrow(features.toArrow()))


@transform
def train_model(
    features: Annotated[pl.DataFrame, Strict(CustomerFeatures)],
) -> LinearRegression:
    return LinearRegression().fit(
        features[["visits", "total_minutes"]],
        features["annual_spend"],
    )


@transform
def print_coefficients(model: LinearRegression) -> None:
    print(f"coefficients: {model.coef_.round(2).tolist()}")


pipeline = Pipeline(SparkContext)
read_activity_step = pipeline.add_step(read_activity)
aggregate_features_step = pipeline.add_step(aggregate_features)
collect_features_step = pipeline.add_step(collect_features)
train_model_step = pipeline.add_step(train_model)
print_coefficients_step = pipeline.add_step(print_coefficients)

read_activity_step >> aggregate_features_step >> collect_features_step
collect_features_step >> train_model_step >> print_coefficients_step

pipeline.run(SparkContext(SparkSession.builder.getOrCreate()))
