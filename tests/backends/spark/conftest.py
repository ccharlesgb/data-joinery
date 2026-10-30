from collections.abc import Generator

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> Generator[SparkSession, None, None]:
    spark = SparkSession.builder.master("local[*]").getOrCreate()
    yield spark
    spark.stop()
