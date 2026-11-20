from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType
from pyspark.testing import assertDataFrameEqual

from data_joinery import Schema

FRAME_TYPES = (pl.DataFrame, pl.LazyFrame, SparkDataFrame)


@dataclass(frozen=True)
class BackendHelper[FrameT]:
    """Provide frame construction and comparison for a frame type under test.

    Attributes:
        frame_type: DataFrame class to create.
        create_options: Backend-specific options for DataFrame creation.
        assert_equal: Assertion helper for comparing two DataFrames.
        from_records: Native constructor for records using the compiled schema.
    """

    frame_type: type[FrameT]
    create_options: dict[str, object]
    assert_equal: Callable[[FrameT, FrameT], bool | None]
    from_records: Callable[[list[dict[str, object]], Schema[Any]], FrameT]

    def create[RowT](self, schema: Schema[RowT], *rows: RowT) -> FrameT:
        """Create a frame from model rows through the public Schema API."""
        return schema.create_dataframe(rows, self.frame_type, **self.create_options)


def _polars_from_records(
    records: list[dict[str, object]], schema: Schema[Any]
) -> pl.DataFrame:
    return pl.DataFrame(records, schema=schema.native_schema(pl.Schema))


def _assert_lazy_frames_equal(actual: pl.LazyFrame, expected: pl.LazyFrame) -> None:
    assert_frame_equal(actual.collect(), expected.collect())


@pytest.fixture(
    params=FRAME_TYPES, ids=["polars-dataframe", "polars-lazyframe", "spark-dataframe"]
)
def dataframe_backend(
    request: pytest.FixtureRequest,
) -> (
    BackendHelper[pl.DataFrame]
    | BackendHelper[pl.LazyFrame]
    | BackendHelper[SparkDataFrame]
):
    """Provide creation options and assertions for the parametrized frame type."""
    if request.param is pl.DataFrame:
        return BackendHelper(
            frame_type=pl.DataFrame,
            create_options={},
            assert_equal=assert_frame_equal,
            from_records=_polars_from_records,
        )
    if request.param is pl.LazyFrame:
        return BackendHelper(
            frame_type=pl.LazyFrame,
            create_options={},
            assert_equal=_assert_lazy_frames_equal,
            from_records=lambda records, schema: _polars_from_records(
                records, schema
            ).lazy(),
        )
    if request.param is not SparkDataFrame:
        pytest.fail(f"No test configuration for {request.param!r}")

    spark: SparkSession = request.getfixturevalue("spark")
    return BackendHelper(
        frame_type=SparkDataFrame,
        create_options={"session": spark},
        assert_equal=assertDataFrameEqual,
        from_records=lambda records, schema: spark.createDataFrame(
            records, schema.native_schema(StructType)
        ),
    )


@pytest.fixture(scope="session")
def spark() -> Generator[SparkSession, None, None]:
    spark = SparkSession.builder.master("local[*]").getOrCreate()
    yield spark
    spark.stop()
