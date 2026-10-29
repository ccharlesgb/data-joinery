from typing import Annotated

from pyspark.ml.feature import VectorAssembler
from pyspark.ml.linalg import VectorUDT
from pyspark.ml.regression import LinearRegression, LinearRegressionModel
from pyspark.sql import DataFrame, SparkSession

from data_joinery import Context, Pipeline, Strict, transform
from data_joinery.backends.spark import SparkContext
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Housing(JoineryModel):
    number_of_bedrooms: Column[int]
    square_footage: Column[int]
    price: Column[float]


class PreparedHousing(JoineryModel):
    number_of_bedrooms: Column[int]
    square_footage: Column[int]
    price: Column[float]
    features: Column[Annotated[object, VectorUDT()]]


@transform
def read_data(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Strict(Housing)]:
    return spark.createDataFrame(
        [
            Housing(number_of_bedrooms=1, square_footage=650, price=180_000.0),
            Housing(number_of_bedrooms=2, square_footage=900, price=260_000.0),
            Housing(number_of_bedrooms=3, square_footage=1_200, price=360_000.0),
            Housing(number_of_bedrooms=4, square_footage=1_600, price=480_000.0),
        ]
    )


@transform
def prepare_features(
    housing: Annotated[DataFrame, Strict(Housing)],
) -> Annotated[DataFrame, Strict(PreparedHousing)]:
    return VectorAssembler(
        inputCols=[Housing.number_of_bedrooms, Housing.square_footage],
        outputCol=PreparedHousing.features,
    ).transform(housing)


@transform
def fit_model(
    housing: Annotated[DataFrame, Strict(PreparedHousing)],
) -> LinearRegressionModel:
    return LinearRegression(
        featuresCol=PreparedHousing.features,
        labelCol=PreparedHousing.price,
        regParam=1e-3,
    ).fit(housing)


@transform
def print_coefficients(model: LinearRegressionModel) -> None:
    print(f"coefficients: {model.coefficients}")
    print(f"intercept: {model.intercept}")


housing_price_model = Pipeline(SparkContext)
read_data_step = housing_price_model.add_step(read_data)
prepare_features_step = housing_price_model.add_step(prepare_features)
fit_model_step = housing_price_model.add_step(fit_model)
print_coefficients_step = housing_price_model.add_step(print_coefficients)

housing_price_model.connect(read_data_step, prepare_features_step)
housing_price_model.connect(prepare_features_step, fit_model_step)
housing_price_model.connect(fit_model_step, print_coefficients_step)

housing_price_model.run(SparkContext(SparkSession.builder.getOrCreate()))
