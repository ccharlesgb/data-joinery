from data_joinery import Column, JoineryModel


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int]


print(Order.price)
print(Order.quantity)
