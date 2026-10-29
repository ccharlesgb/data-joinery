from typing import Annotated

from pyspark.sql import DataFrame, SparkSession
from pyspark.testing import assertDataFrameEqual

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


@transform
def filter_active_customers(
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(Customer)]:
    return customers.filter(customers[Customer.is_active])


def test_filter_active_customers():
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
    expected_active_customers = customer_schema.create_dataframe(
        [
            Customer(customer_id="1", name="Alice", is_active=True),
            Customer(customer_id="3", name="Charlie", is_active=True),
        ],
        DataFrame,
        session=spark,
    )

    active_customers = customers.transform(filter_active_customers)
    assertDataFrameEqual(active_customers, expected_active_customers)
