# Testing

You can unit test your transformations in the same way you would normally but now because
you have already defined the input and output schemas for your production code you can now
use them as a convenient way to produce input fixtures for your tests:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/transform/testing/test_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/testing/test_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/transform/testing/test_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/testing/test_example_spark_stdout.log"
    ```
