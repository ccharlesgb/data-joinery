# Defining a Schema

Schemas wrap around [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/#basic-model-usage)
or Python [dataclasses](https://docs.python.org/3/library/dataclasses.html). They allow you to define the
structure of your data in a backend agnostic way. The same schema can be used to define a schema for any
backend you choose.

## Dataclasses

Take the below example for a simple dataclass schema:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_example_stdout.log"
```

The method [native_schema](/reference/schemas/#data_joinery.Schema.native_schema) can be used to
generate the schema for a specific backend, such as PySpark or Polars.

It doesn't matter what dataclass configuration you choose (frozen, slots, etc.) However if you decide to
use dataclass inheritence it is best practice to use `kw_only=True` to avoid issues with field ordering:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_inheritance_example_stdout.log"
```

The field order will follow standard dataclass [rules](https://docs.python.org/3/library/dataclasses.html#inheritance)

## Pydantic models

The same example schema can be defined with Pydantic as well:

``` python
--8<-- "docs_src/learn/schemas/index/pydantic_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/index/pydantic_example_stdout.log"
```

??? warning "Pydantic field validation is not enforced"

    Data Joinery does not enforce Pydantic validation rules. It can be useful to include them in your models for
    documentation and for generating valid test fixtures, but only the data type is enforced.

## Nested schemas

If you have nested data contains structs or arrays then this is easy to express with nested
dataclasses or Pydantic models:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_example_nested.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/index/dataclass_nested_example_stdout.log"
```
