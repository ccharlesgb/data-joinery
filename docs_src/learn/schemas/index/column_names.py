from data_joinery.schemas.joinery_model import Column, JoineryModel, column


class OrderTotal(JoineryModel):
    total_price: Column[float] = column(name="Total Price")


print(OrderTotal.total_price)
