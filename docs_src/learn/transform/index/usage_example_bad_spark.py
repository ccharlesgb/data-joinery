import traceback
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import (
    Column,
    JoineryModel,
    Schema,
    SchemaCoercionError,
    Strict,
    transform,
)


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


class CustomerCount(JoineryModel):
    customer_count: Column[int]


@transform
def filter_active_customers(
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(Customer)]:
    return customers.filter(customers[Customer.is_active])


@transform
def get_customer_count(
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(CustomerCount)]:
    return customers.groupBy().count()


spark = SparkSession.builder.getOrCreate()

customer_schema = Schema(Customer)

customers = customer_schema.create_dataframe(
    [
        Customer(customer_id="1", name="Alice", is_active=True),
        Customer(customer_id="2", name="Bob", is_active=False),
        Customer(customer_id="3", name="Charlie", is_active=True),
    ],
    DataFrame,
    session=spark,
)
try:
    customers.transform(filter_active_customers).transform(get_customer_count)
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
