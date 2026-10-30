from typing import Annotated, cast

import polars as pl
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from sklearn.linear_model import LinearRegression

from data_joinery import Context, Pipeline, Strict, transform
from data_joinery.backends.spark import SparkContext
from data_joinery.schemas.joinery_model import Column, JoineryModel


class CustomerActivity(JoineryModel):
    customer_id: Column[int]
    minutes: Column[int]
    annual_spend: Column[float]


class CustomerFeatures(JoineryModel):
    customer_id: Column[int]
    visits: Column[int]
    total_minutes: Column[int]
    annual_spend: Column[float]


@transform
def read_activity(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Strict(CustomerActivity)]:
    return spark.createDataFrame(
        [
            CustomerActivity(customer_id=1, minutes=10, annual_spend=2_700.0),
            CustomerActivity(customer_id=1, minutes=20, annual_spend=2_700.0),
            CustomerActivity(customer_id=2, minutes=15, annual_spend=4_000.0),
            CustomerActivity(customer_id=2, minutes=15, annual_spend=4_000.0),
            CustomerActivity(customer_id=2, minutes=20, annual_spend=4_000.0),
            CustomerActivity(customer_id=3, minutes=25, annual_spend=2_000.0),
            CustomerActivity(customer_id=4, minutes=20, annual_spend=5_700.0),
            CustomerActivity(customer_id=4, minutes=20, annual_spend=5_700.0),
            CustomerActivity(customer_id=4, minutes=20, annual_spend=5_700.0),
            CustomerActivity(customer_id=4, minutes=20, annual_spend=5_700.0),
            CustomerActivity(customer_id=5, minutes=20, annual_spend=3_300.0),
            CustomerActivity(customer_id=5, minutes=25, annual_spend=3_300.0),
        ]
    )


@transform
def aggregate_features(
    activity: Annotated[DataFrame, Strict(CustomerActivity)],
) -> Annotated[DataFrame, Strict(CustomerFeatures)]:
    return activity.groupBy(CustomerActivity.customer_id).agg(
        F.count("*").alias(CustomerFeatures.visits),
        F.sum(CustomerActivity.minutes).alias(CustomerFeatures.total_minutes),
        F.max(CustomerActivity.annual_spend).alias(CustomerFeatures.annual_spend),
    )


@transform
def collect_features(
    features: Annotated[DataFrame, Strict(CustomerFeatures)],
) -> Annotated[pl.LazyFrame, Strict(CustomerFeatures)]:
    return cast(pl.DataFrame, pl.from_arrow(features.toArrow())).lazy()


@transform
def train_model(
    features: Annotated[pl.LazyFrame, Strict(CustomerFeatures)],
) -> LinearRegression:
    collected = features.collect()
    return LinearRegression().fit(
        collected[[CustomerFeatures.visits, CustomerFeatures.total_minutes]],
        collected[CustomerFeatures.annual_spend],
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
