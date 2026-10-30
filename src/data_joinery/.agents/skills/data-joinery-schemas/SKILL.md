---
name: data-joinery-schemas
description: Define and use Data Joinery schemas with JoineryModel, including column names, nested fields, backend type overrides, DataFrame fixtures, and coercion modes. Use for schema/model and test-data tasks, not transform graphs.
---

# Data Joinery Schemas

Model the logical record shape first, then use `Schema(Model)` for backend-specific operations.
Schemas can be used independently of transforms and pipelines.

## Define a Model

Prefer `JoineryModel` with each field annotated as `Column[T]`, where `T` is the Python value type.
No `@dataclass` decorator is needed:

```python
from data_joinery import Column, JoineryModel, Schema, column


class Customer(JoineryModel):
    """Columns describing a customer."""

    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


customer_schema = Schema(Customer)
```

Class attributes such as `Customer.customer_id` return column names for DataFrame expressions;
instance attributes hold row values. Constructors require keyword arguments. Use
`column(name="Display Name")` to override a column name while keeping the Python attribute name
as the constructor argument. Configure defaults with `column(default=...)` or
`column(default_factory=...)`.

Nested models become struct fields. Use `Column[Employee]` for a nested model and
`Column[list[Employee]]` for a list of nested models.

Dataclasses and Pydantic models are also supported. For dataclass inheritance, prefer
`@dataclass(kw_only=True)` for base and derived models to avoid field-ordering issues.

Pydantic constraints and validators can document models and produce valid model instances, but
Data Joinery enforces field data types only. It does not apply Pydantic field validation to
DataFrame values.

## Compile for a Backend

Pass the backend's schema class to `native_schema`:

```python
import polars as pl
from pyspark.sql.types import StructType

spark_schema = customer_schema.native_schema(StructType)
polars_schema = customer_schema.native_schema(pl.Schema)
```

The default mappings include `int` to Spark `LongType()` or Polars `Int64`, and `float` to Spark
`DoubleType()` or Polars `Float64`. Strings, booleans, dates, timestamps, durations, decimals, and
binary values similarly map to their native backend types.

Override an ambiguous or unsuitable default with `typing.Annotated`. Metadata is selected by
backend, and one field can carry overrides for both backends:

```python
from typing import Annotated

import polars as pl
from pyspark.sql.types import ShortType


class Measurement(JoineryModel):
    """A measurement with backend-specific integer types."""

    value: Column[Annotated[int, ShortType(), pl.Int16]]
```

Do not assume equivalent widths exist across backends. Crossing backends can overflow or lose
precision if their explicit types differ.

Spark nullability is not a Data Joinery data-quality guarantee. When coercing, Data Joinery makes
Spark fields nullable, including nested struct fields and array or map values. Add explicit value
validation when nulls must be forbidden.

## Create Fixture DataFrames

Use model instances as concise, typed test rows and pass the desired DataFrame class:

```python
from pyspark.sql import DataFrame

rows = [
    Customer(customer_id="1", name="Alice", is_active=True),
    Customer(customer_id="2", name="Bob", is_active=False),
]
customers = customer_schema.create_dataframe(rows, DataFrame, session=spark)
```

For Polars, pass `pl.LazyFrame` by default, or `pl.DataFrame` when an eager frame is useful; no
Spark session is required. Prefer this API for fixtures because the same model defines both the
row values and expected backend schema. Coercion also accepts either Polars type and preserves
the frame type. Collect a lazy result when its values are needed, such as for a test comparison.
Construct the expected frame and compare the complete value with
`polars.testing.assert_frame_equal(actual.collect(), expected)` for a lazy result, or compare
eager Polars and PySpark results with their respective `assert_frame_equal` and
`assertDataFrameEqual` helpers.

## Coerce an Existing DataFrame

Call `Schema(Model).coerce_dataframe(frame, mode=...)`. Choose the least permissive mode that fits
the boundary:

- `"strict"` is the default and requires exactly the model's named fields and types. Extra fields, missing fields,
  and type mismatches fail. Field order and nullability are ignored, and input order is preserved.
- `"project_top_level"` removes extra top-level columns, but nested structs must already match.
- `"project"` recursively removes extra top-level and nested fields. Missing
  fields and type mismatches still fail.
- `"project_cast"` recursively projects fields and asks the backend to cast values to model types.
  Missing fields still fail, and a permitted cast can still fail for a particular runtime value.

Use strict validation for controlled internal boundaries. Use projection for wide external tables
where the model intentionally declares only consumed fields. Use casting only when source type
normalization is an intended part of the boundary.

When documenting an expected failure in this repository, catch the specific exception, such as
`SchemaCoercionError`, so the runnable documentation snippet still exits successfully.
