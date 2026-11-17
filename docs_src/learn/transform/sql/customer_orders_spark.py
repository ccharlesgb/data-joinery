from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Column, JoineryModel, Strict, transform


class Order(JoineryModel):
    """An order and the customer who placed it."""

    order_id: Column[str]
    customer_id: Column[str]


class Customer(JoineryModel):
    """A customer and their display name."""

    customer_id: Column[str]
    name: Column[str]


class CustomerOrder(JoineryModel):
    """An order with its customer's name."""

    order_id: Column[str]
    customer_name: Column[str]


@transform
def customer_orders(
    orders: Annotated[DataFrame, Strict(Order)],
    customers: Annotated[DataFrame, Strict(Customer)],
) -> Annotated[DataFrame, Strict(CustomerOrder)]:
    """Look up the customer name for each matching order."""
    return orders.sparkSession.sql(
        """
        SELECT o.order_id, c.name AS customer_name
        FROM {orders} AS o
        JOIN {customers} AS c ON o.customer_id = c.customer_id
        ORDER BY o.order_id
        """,
        orders=orders,
        customers=customers,
    )


spark = SparkSession.builder.getOrCreate()
orders = spark.createDataFrame([("A", "2"), ("B", "1")], ["order_id", "customer_id"])
customers = spark.createDataFrame(
    [("1", "Alice"), ("2", "Bob")], ["customer_id", "name"]
)

result = customer_orders(orders, customers)
result.show()
