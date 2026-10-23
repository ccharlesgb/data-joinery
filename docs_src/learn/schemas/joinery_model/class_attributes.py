from dataclasses import dataclass

from data_joinery.schemas.joinery_model import Column, JoineryModel, column


@dataclass
class DataclassOrder:
    """An order defined with a normal dataclass."""

    price: float
    quantity: int = 1


class JoineryOrder(JoineryModel):
    """An order with column names available on the class."""

    price: Column[float]
    quantity: Column[int] = column(default=1)


# A required dataclass field has no class attribute.
print("DataclassOrder has a price attribute:", hasattr(DataclassOrder, "price"))
print("DataclassOrder.quantity:", DataclassOrder.quantity)

# JoineryModel class attributes return column names, even for defaulted fields.
print("JoineryOrder.price:", JoineryOrder.price)
print("JoineryOrder.quantity:", JoineryOrder.quantity)

# Both instances return the stored values.
plain_order = DataclassOrder(price=12.5)
joinery_order = JoineryOrder(price=12.5)
print("Dataclass instance:", plain_order.price, plain_order.quantity)
print("JoineryModel instance:", joinery_order.price, joinery_order.quantity)
