from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class SubModel(JoineryModel):
    subfield1: Column[str]
    subfield2: Column[str]


class Model(JoineryModel):
    field1: Column[str]
    field2: Column[str]
    sub_schema: Column[SubModel]


schema = Schema(Model)
