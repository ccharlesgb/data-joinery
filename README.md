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
can make it much clearer:

``` python
from dataclasses import dataclass
from datetime import date
from typing import Annotated

import polars as pl

from data_joinery import Strict, transform


@dataclass
class Customer:
    snapshot_date: date
    customer_id: str
    name: str
    is_active: bool
    package: str


@dataclass
class CustomerMetrics:
    snapshot_date: date
    total_customer_count: int
    active_customer_count: int
    basic_package_customer_count: int
    pro_package_customer_count: int


@transform
def get_metrics(
    fact_table: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(CustomerMetrics)]: ...
```

Using a schema first approach makes it much clearer what this transformation does, for
both you and a coding agent. Data Joinery will also enforce at runtime that the input and output
schemas match the type annotations.
