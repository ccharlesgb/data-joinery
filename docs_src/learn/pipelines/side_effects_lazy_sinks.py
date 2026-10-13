from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from data_joinery import Pipeline, side_effect, transform

with TemporaryDirectory() as directory:
    parquet_path = Path(directory) / "orders.parquet"
    ipc_path = Path(directory) / "orders.ipc"

    @transform
    def make_orders() -> pl.LazyFrame:
        return pl.LazyFrame({"order_id": [1, 2], "amount": [10, 25]})

    @transform
    def write_parquet(orders: pl.LazyFrame) -> pl.LazyFrame:
        return orders.sink_parquet(parquet_path, lazy=True)

    @transform
    def write_ipc(orders: pl.LazyFrame) -> pl.LazyFrame:
        return orders.sink_ipc(ipc_path, lazy=True)

    @side_effect
    def collect_sinks(parquet: pl.LazyFrame, ipc: pl.LazyFrame) -> None:
        pl.collect_all([parquet, ipc])
        print(f"Wrote {parquet_path.name} and {ipc_path.name}")

    pipeline = Pipeline()
    orders = pipeline.add_step(make_orders)
    parquet = pipeline.add_step(write_parquet)
    ipc = pipeline.add_step(write_ipc)
    collect = pipeline.add_step(collect_sinks)
    orders >> parquet
    orders >> ipc
    pipeline.connect(parquet, collect, param="parquet")
    pipeline.connect(ipc, collect, param="ipc")
    pipeline.run()
