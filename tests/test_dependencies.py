from dataclasses import dataclass
from typing import Any

import pytest
from pyspark.sql import SparkSession

from data_joinery.backends.spark import SparkContext
from data_joinery.dependencies import inspect_context_type


@dataclass(frozen=True)
class PathConfig:
    value: str


@dataclass(frozen=True)
class ValidContext:
    path: PathConfig
    retries: int


def test_inspect_context_type_maps_dependency_types_to_fields():
    assert inspect_context_type(ValidContext) == {
        PathConfig: "path",
        int: "retries",
    }


def test_spark_context_provides_spark_session():
    assert inspect_context_type(SparkContext) == {SparkSession: "spark"}


def test_inspect_context_type_rejects_non_dataclass():
    class NotAContext:
        pass

    with pytest.raises(TypeError, match="must be a dataclass"):
        inspect_context_type(NotAContext)


def test_inspect_context_type_rejects_duplicate_dependency_types():
    @dataclass
    class DuplicateContext:
        input_path: PathConfig
        output_path: PathConfig

    with pytest.raises(TypeError, match="both provide PathConfig"):
        inspect_context_type(DuplicateContext)


def test_inspect_context_type_rejects_non_runtime_dependency_type():
    @dataclass
    class InvalidContext:
        paths: list[PathConfig]

    with pytest.raises(TypeError, match="unsubscripted runtime classes"):
        inspect_context_type(InvalidContext)


def test_inspect_context_type_rejects_any_dependency_type():
    @dataclass
    class InvalidContext:
        value: Any

    with pytest.raises(TypeError, match="unsubscripted runtime classes"):
        inspect_context_type(InvalidContext)
