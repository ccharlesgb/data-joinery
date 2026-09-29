from typing import Any, Protocol

from pyspark.sql import DataFrame


class Dbt(Protocol):
    """The dbt runtime interface used by Python models.

    A dbt Python model receives an object implementing this protocol as its
    ``dbt`` argument. Declaring the protocol in a pipeline context allows
    transforms to resolve dbt models and sources without depending on dbt's
    concrete runtime implementation which is generated dynamically.
    """

    def config(self, *args: Any, **kwargs: Any) -> None: ...

    def ref(self, name: str) -> DataFrame: ...

    def source(self, source_name: str, table_name: str) -> DataFrame: ...
