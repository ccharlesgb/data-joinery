from data_joinery.schemas.joinery_model import Column, JoineryModel


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int]


print(Order.price)
print(Order.quantity)
