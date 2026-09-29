# Mixing Backends

It is possible to write a transformation that takes a dataframe in one backend and outputs it in another. A common
use case of this is to collect a spark frame to a Polars dataframe onto the driver node after an
aggregation.

This example moves the records from Polars to Spark and then to Polars; it does not change
their values or columns. `record_id` uses `Annotated` metadata to give the same Python `int` a
different explicit representation in every backend: Polars `UInt32`, Spark `LongType`, and Polars
`UInt16`.

``` python
--8<-- "docs_src/learn/transform/mixing_backends.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/transform/mixing_backends_stdout.log"
```
