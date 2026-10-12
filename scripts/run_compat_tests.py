"""Check the selected backend versions before running the test suite."""

import sys

import polars
import pyspark
import pytest


def main() -> int:
    expected_spark, expected_polars = sys.argv[1:]
    actual_spark = pyspark.__version__
    actual_polars = polars.__version__
    print(f"PySpark {actual_spark}; Polars {actual_polars}", flush=True)

    if not actual_spark.startswith(f"{expected_spark}."):
        raise RuntimeError(f"Expected PySpark {expected_spark}.x, got {actual_spark}")
    if not actual_polars.startswith(f"{expected_polars}."):
        raise RuntimeError(f"Expected Polars {expected_polars}.x, got {actual_polars}")

    return pytest.main(["--ignore=docs_src/"])


if __name__ == "__main__":
    sys.exit(main())
