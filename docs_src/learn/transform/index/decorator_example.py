from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Project, Strict, transform
from data_joinery.schemas import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


@transform
def filter_active_customers(
    customers: Annotated[DataFrame, Project(Customer)],
) -> Annotated[DataFrame, Strict(Customer)]:
    return customers.filter(customers.is_active)


spark = SparkSession.builder.getOrCreate()

customers = Schema(Customer).create_dataframe(
    [
        Customer(customer_id="1", name="Alice", is_active=True),
        Customer(customer_id="2", name="Bob", is_active=False),
        Customer(customer_id="3", name="Charlie", is_active=True),
    ],
    DataFrame,
    session=spark,
)

active_customers = filter_active_customers(customers)
active_customers.show()
