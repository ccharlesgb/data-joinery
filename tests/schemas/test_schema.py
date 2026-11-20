from collections.abc import Callable
from dataclasses import dataclass

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession
from pyspark.testing import assertDataFrameEqual

from data_joinery import Column, JoineryModel, Schema
from data_joinery.schemas import CoercionMode


@dataclass(frozen=True)
class BackendHelper[FrameT]:
    """Provide frame construction and comparison for a backend under test.

    Attributes:
        frame_type: DataFrame class to create.
        create_options: Backend-specific options for DataFrame creation.
        assert_equal: Assertion helper for comparing two DataFrames.
    """

    frame_type: type[FrameT]
    create_options: dict[str, object]
    assert_equal: Callable[[FrameT, FrameT], bool | None]


@pytest.fixture(params=["polars", "spark"])
def dataframe_backend(
    request: pytest.FixtureRequest,
) -> BackendHelper[pl.DataFrame] | BackendHelper[SparkDataFrame]:
    if request.param == "polars":
        return BackendHelper(
            frame_type=pl.DataFrame, create_options={}, assert_equal=assert_frame_equal
        )
    spark: SparkSession = request.getfixturevalue("spark")
    return BackendHelper(
        frame_type=SparkDataFrame,
        create_options={"session": spark},
        assert_equal=assertDataFrameEqual,
    )


def test_schema_rejects_a_non_schema_model() -> None:
    class NotASchemaModel:
        pass

    with pytest.raises(
        ValueError,
        match="NotASchemaModel is neither a dataclass nor a pydantic model",
    ):
        Schema(NotASchemaModel)


@pytest.mark.parametrize("mode", ["project", "project_cast"])
def test_projection_preserves_null_structs[FrameT](
    dataframe_backend: BackendHelper[FrameT], mode: CoercionMode
) -> None:
    class ProjectedNested(JoineryModel):
        value: Column[int | None]

    class SourceNested(ProjectedNested):
        extra: Column[int]

    class SourceRow(JoineryModel):
        nested: Column[SourceNested | None]
        items: Column[list[SourceNested | None]]

    class ProjectedRow(JoineryModel):
        nested: Column[ProjectedNested | None]
        items: Column[list[ProjectedNested | None]]

    source_nested = SourceNested(value=None, extra=1)
    projected_nested = ProjectedNested(value=None)
    source = Schema(SourceRow).create_dataframe(
        [
            SourceRow(nested=None, items=[None, source_nested]),
            SourceRow(nested=source_nested, items=[]),
        ],
        dataframe_backend.frame_type,
        **dataframe_backend.create_options,
    )
    projection = Schema(ProjectedRow)
    expected = projection.create_dataframe(
        [
            ProjectedRow(nested=None, items=[None, projected_nested]),
            ProjectedRow(nested=projected_nested, items=[]),
        ],
        dataframe_backend.frame_type,
        **dataframe_backend.create_options,
    )

    actual = projection.coerce_dataframe(source, mode)

    dataframe_backend.assert_equal(actual, expected)
