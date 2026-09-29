# Adding a dataframe backend

A backend translates the backend-neutral `ModelSchema` into a native schema and owns all
dataframe-specific creation, projection, and casting. Implement the
`DataFrameBackend` protocol and register one instance:

``` python
--8<-- "docs_src/internals/backends.py"
```

The backend is selected from either the dataframe class or native schema class supplied through
the public API. Keep native type inference and cast rules inside the backend, and add its tests
under `tests/backends/`. Registration rejects duplicate names and overlapping dataframe or schema
types.

Once registered, use the backend's dataframe class in a transform as usual:

``` python
@transform
def select_orders(
    orders: Annotated[ExampleDataFrame, Project(Order)],
) -> Annotated[ExampleDataFrame, Strict(Order)]:
    return orders
```
