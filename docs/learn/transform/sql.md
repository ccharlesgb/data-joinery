# Using SQL in a transform

You can write a SQL query inside an `@transform` function. Pass each input DataFrame
to the SQL backend under the name you want to use in the query.

The example below joins orders to customers to look up the customer name for each
order:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/transform/sql/customer_orders_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/transform/sql/customer_orders_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/transform/sql/customer_orders_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/transform/sql/customer_orders_spark_stdout.log"
    ```
