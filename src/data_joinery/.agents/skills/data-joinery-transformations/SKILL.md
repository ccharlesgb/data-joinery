---
name: data-joinery-transformations
description: Define, run, and unit test Data Joinery transforms with explicit DataFrame contracts and backend-aware fixtures. Use for individual transformation behavior; use the pipeline skill for graph construction and end-to-end tests.
---

# Data Joinery Transformations

Decorate an ordinary function with `@transform` and express each DataFrame contract as
`Annotated[DataFrameType, Coercion(Model)]`. Data Joinery coerces and validates contracted inputs
and outputs at runtime.

## Define Contracts Deliberately

```python
from typing import Annotated

from pyspark.sql import DataFrame

from data_joinery import Project, Strict, transform


@transform
def filter_active_customers(
    customers: Annotated[DataFrame, Project(Customer)],
) -> Annotated[DataFrame, Strict(Customer)]:
    return customers.filter(customers.is_active)
```

The contract marker determines boundary behavior:

- `Strict(Model)` requires exactly the named fields and types; field order and nullability do not
  matter.
- `ProjectTopLevel(Model)` removes extra top-level columns but requires nested structs to match.
- `Project(Model)` recursively removes undeclared fields and is useful for inputs from wide or
  nested source tables.
- `ProjectCast(Model)` recursively projects and casts using backend rules.

Missing fields fail in every projection mode. Prefer permissive inputs and strict outputs when a
transform consumes part of a wider record but owns its result shape. A reader for a wide or deeply
nested external table can intentionally use `Project` on its output to declare only the fields the
application consumes.

Keep all DataFrame inputs and outputs annotated. This makes a transform understandable and
composable. A transform can change backends by using different DataFrame classes in its input and
return annotations. Perform the conversion explicitly in the body and define backend-specific
model field types with `Annotated` metadata where needed.

Transforms can also accept or return ordinary class instances. These contracts check runtime class
compatibility rather than coercing a schema. Parameterized instance types such as `list[str]` are
not supported; wrap structured values in a named class when their contents matter.

## Run a Transform

Call the decorated function normally or use a backend's transform idiom, such as Spark's
`frame.transform(my_transform)`. Contract failures raise `SchemaCoercionError`. Spark is lazy, so
schema validation often happens before computation, but actions inside a transform can perform
substantial work before an output error is observed.

## Unit Test One Transform

Test the transform as an ordinary function. Build fixtures from the same models used by production
contracts:

```python
from pyspark.testing import assertDataFrameEqual

from data_joinery import Schema


def test_filter_active_customers(spark):
    schema = Schema(Customer)
    source = schema.create_dataframe(
        [Customer("1", "Alice", True), Customer("2", "Bob", False)],
        DataFrame,
        session=spark,
    )
    expected = schema.create_dataframe(
        [Customer("1", "Alice", True)],
        DataFrame,
        session=spark,
    )

    actual = filter_active_customers(source)

    assertDataFrameEqual(actual, expected)
```

Use a shared local Spark fixture when the project has one rather than creating a new session in
every test. For Polars, use its DataFrame testing assertions. Assert values as well as schema so a
contract-valid but logically incorrect result cannot pass.

Add focused failure tests when contract behavior is part of the requirement. For example, verify
that a missing required field or incorrect output name raises `SchemaCoercionError`. Do not retest
the decorator in every transform test; test business behavior and any boundary choice unique to
that transform.
