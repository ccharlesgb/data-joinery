# Overriding types

Types can be overridden for a specific backend by annotating the fields in your models. If you need to
override the default type for multiple backends you can just annotate more than once. Take this
example schema where we override the default types for a python `int`. Only if the annotation is present
for the backend does the type get overridden. The tabs show backend-specific overrides for the same Python field types:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/overriding_types/annotated_example_intro_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/overriding_types/annotated_example_intro_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/overriding_types/annotated_example_intro_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/overriding_types/annotated_example_intro_spark_stdout.log"
    ```

## Backend specific type behaviour

It isn't a perfect mapping between Python types and backend-specific types, and there may not be
equivalent types between Polars and PySpark as well. The backends offer different integer widths, so converting a frame between them may
change the available precision or raise an overflow error.

### Spark

By default Data Joinery will use the documented [conversions](https://spark.apache.org/docs/latest/api/python/tutorial/sql/type_conversions.html#all-conversions) to map Python
types to Spark types. However,
this might not be suitable for all use cases for example if you have a `DecimalType` or `VarcharType`. These types
cannot be expressed in normal Python so you have to use `Annotated` to override the type in the schema.

There are also some Python types that can map to multiple spark types and this module has made a
choice. For example `int` -> `LongType` and `float` -> `DoubleType`. For a full list of default mappings
see [default type mappings.](../../reference/type_mapping.md#spark)

The below example shows the effect of annotating your fields has on the resulting schema:

``` python
--8<-- "docs_src/learn/schemas/annotated_example_spark.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/annotated_example_spark_stdout.log"
```

!!! warning "Nullability in Spark"

    Nullability is a bit tricky in Spark. `nullable=False` is information Spark can use while
    planning a query, not a data-quality constraint. Data Joinery therefore makes every field nullable,
    including nested struct fields and array or map values, whenever it coerces a DataFrame.
    Use explicit validation when a column must not contain null values.

### Polars

Polars type mapping can be found in the default
[type mappings reference.](../../reference/type_mapping.md#polars).
