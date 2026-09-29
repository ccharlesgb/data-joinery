# Defining Schemas

This is the lowest level use of Data Joinery. Schemas can be defined using [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/#basic-model-usage) or Python [dataclasses](https://docs.python.org/3/library/dataclasses.html). Either will work but Pydantic has the
slight advantage of being able to define validation rules for test fixtures.

The native type passed to `Schema.native_schema()` selects the schema backend. The examples in
this guide use Spark's `StructType`, so the result is statically typed as a Spark schema.

## Dataclasses

A dataclass schema is defined using the standard Python `dataclass` decorator. Each field in the dataclass corresponds to a column in the Spark dataframe.

``` python
--8<-- "docs_src/learn/schemas/dataclass_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/dataclass_example_stdout.log"
```

If your data has arrays or nested structures you can define these by nesting the dataclasses as you
would in native python:

``` python
--8<-- "docs_src/learn/schemas/dataclass_example_nested.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/dataclass_example_nested_stdout.log"
```

## Pydantic Models

Pydantic models work in the same way:

``` python
--8<-- "docs_src/learn/schemas/pydantic_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/pydantic_example_stdout.log"
```

??? warning "Pydantic field validation is not enforced"

    Data Joinery does not enforce Pydantic validation rules. It can be useful to include them in your models for
    documentation and for generating valid test fixtures, but only the data type is enforced.

## Creating Dataframes from model instances

You can easily create example DataFrames from lists of model instances. This is particularly
useful for building test fixtures for a transformation. Pass the desired frame class to select
its backend. Spark also requires its session through the `session` keyword. The returned value is
statically typed as the requested frame class.

``` python
--8<-- "docs_src/learn/schemas/fixture_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/fixture_example_stdout.log"
```

## Default types and manually setting data types

By default Data Joinery will use the documented [conversions](https://spark.apache.org/docs/latest/api/python/tutorial/sql/type_conversions.html#all-conversions) to map Python
types to Spark types. However,
this might not be suitable for all use cases for example if you have a `DecimalType` or `VarcharType`. These types
cannot be expressed in normal Python so you have to use `Annotated` to override the type in the schema.

There are also some Python types that can map to multiple spark types and this module has made a
choice. For example `int` -> `LongType` and `float` -> `DoubleType`. For a full list of default mappings
see [default type mappings.](/reference/type_mapping/)

The below example shows the effect of annotating your fields has on the resulting schema:

``` python
--8<-- "docs_src/learn/schemas/annotated_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/annotated_example_stdout.log"
```

## A note on nullability

Nullability is a bit tricky in Spark. `nullable=False` is information Spark can use while planning a query, not a data-quality constraint. Data Joinery therefore makes every field nullable, including nested struct fields and array or map values, whenever it coerces a DataFrame. Use explicit validation when a column must not contain null values.
