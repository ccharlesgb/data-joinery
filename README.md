# Data Joinery

---

**Documentation**: [https://ccharlesgb.github.io/data-joinery/](https://ccharlesgb.github.io/data-joinery/)

**Examples**: [https://github.com/ccharlesgb/data-joinery-examples](https://github.com/ccharlesgb/data-joinery-examples)

---

Data Joinery is a small framework that allows you to build complex transformation jobs with an emphasis on
testability. It helps you break apart complex transformations into testable units, whilst
allowing you to annotate these transformations with the upstream/downstream schemas.
Without a schema contract, a transformation might be declared as:

``` python
def get_metrics(fact_table: pl.LazyFrame) -> pl.LazyFrame: ...
```

From this we have no idea what the inputs or outputs of the transformation are. With Data Joinery you
can make it much clearer by defining schemas with `JoineryModel`. Annotate each field with `Column[T]`,
where `T` is the field's Python type:

``` python
from datetime import date
from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Strict, transform


class Customer(JoineryModel):
    """Input columns for a customer."""

    snapshot_date: Column[date]
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]
    package: Column[str]


class CustomerMetrics(JoineryModel):
    """Customer counts for each snapshot date."""

    snapshot_date: Column[date]
    total_customer_count: Column[int]
    active_customer_count: Column[int]
    basic_package_customer_count: Column[int]
    pro_package_customer_count: Column[int]


@transform
def get_metrics(
    fact_table: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(CustomerMetrics)]: ...
```

Using a schema first approach makes it much clearer what this transformation does, for
both you and a coding agent. Data Joinery will also enforce at runtime that the input and output
schemas match the type annotations.
