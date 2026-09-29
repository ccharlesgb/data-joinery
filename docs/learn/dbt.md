# dbt Integration

!!! example

    The dbt integration is experimental

Data Joinery pipelines can run inside dbt Python models. Put dbt's runtime object in the pipeline
context, then use it in reader transformations to fetch upstream models and sources.

``` python
--8<-- "docs_src/learn/dbt/dbt_pipeline.py"
```
