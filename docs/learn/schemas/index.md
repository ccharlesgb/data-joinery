# Defining a Schema

Schemas wrap around [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/#basic-model-usage)
or Python [dataclasses](https://docs.python.org/3/library/dataclasses.html). They allow you to define the
structure of your data in a backend agnostic way. The same schema can be used to define a schema for any
backend you choose.

## Dataclasses

Take the below example for a simple dataclass schema:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_example_spark_stdout.log"
    ```

The method [native_schema](/reference/schemas/#data_joinery.Schema.native_schema) can be used to
generate the schema for a specific backend, such as PySpark or Polars.

It doesn't matter what dataclass configuration you choose (frozen, slots, etc.) However if you decide to
use dataclass inheritance it is best practice to use `kw_only=True` to avoid issues with field ordering:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example_spark_stdout.log"
    ```

The field order will follow standard dataclass [rules](https://docs.python.org/3/library/dataclasses.html#inheritance)

## Pydantic models

The same example schema can be defined with Pydantic as well:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/pydantic_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/pydantic_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/pydantic_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/pydantic_example_spark_stdout.log"
    ```

??? warning "Pydantic field validation is not enforced"

    Data Joinery does not enforce Pydantic validation rules. It can be useful to include them in your models for
    documentation and for generating valid test fixtures, but only the data type is enforced.

## Nested schemas

If your data contains nested structs or arrays, describe them with nested dataclasses
or Pydantic models:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_example_nested_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_example_nested_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/dataclass_example_nested_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/dataclass_example_nested_spark_stdout.log"
    ```
