import traceback
from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Schema, Strict, transform
from data_joinery.schema_types import SchemaCoercionError


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


@dataclass
class CustomerCount:
    customer_count: int


@transform
def filter_active_customers(
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(Customer)]:
    return customers.filter(customers.is_active)


@transform
def get_customer_count(
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(CustomerCount)]:
    return customers.groupBy().count()


spark = SparkSession.builder.appName("example").getOrCreate()

customer_schema = Schema(Customer)

customers = customer_schema.create_dataframe(
    [
        Customer("1", "Alice", True),
        Customer("2", "Bob", False),
        Customer("3", "Charlie", True),
    ],
    DataFrame,
    session=spark,
)
try:
    customers.transform(filter_active_customers).transform(get_customer_count)
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
