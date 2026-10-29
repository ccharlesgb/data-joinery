from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


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
    return (
        customers.groupBy()
        .count()
        .withColumnRenamed("count", CustomerCount.customer_count)
    )


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

active_customer_count = customers.transform(filter_active_customers).transform(
    get_customer_count
)
active_customer_count.show()
