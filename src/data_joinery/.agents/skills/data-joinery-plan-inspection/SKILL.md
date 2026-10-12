---
name: data-joinery-plan-inspection
description: Inspect and compare PySpark or Polars query plans produced by Data Joinery pipelines when investigating scans, joins, caching, shuffles, or performance. Use for execution plans, not pipeline graph diagrams.
---

# Inspect Data Joinery Query Plans

Inspect the DataFrame query at the execution boundary. The Data Joinery graph shows step
connections, while the backend's explain API shows how a DataFrame will be evaluated.

## Obtain the plan without writing outputs

Run the pipeline with `include_side_effects=False`, then retrieve the last model step's
output with `result.get_output("step_name", FrameType)` or a retained `Step`. A skipped
`@side_effect` writer has no invocation to inspect. An unmarked transform that constructs
and returns a lazy sink still runs, so its output can be inspected as a `pl.LazyFrame`.

This option skips only marked side effects. Reader validation or other unmarked transforms
may already execute actions, so inspect them before using large or external inputs. Use a
safe context or reader overrides when needed; keep representative schemas and data sizes
for performance comparisons.

## PySpark

```python
from pyspark.sql import DataFrame

result = pipeline.run(context, include_side_effects=False)
frame = result.get_output("build_report", DataFrame)
frame.explain(mode="extended")   # parsed, analyzed, optimized, and physical plans
frame.explain(mode="formatted")  # readable physical plan
```

Inspect scans and pushed filters, join strategies, `Exchange`/shuffle and sort nodes,
partitioning, and estimated statistics when available. `explain` does not run the
DataFrame action, and an adaptive plan may change during execution. For actual runtime
behavior, run the intended action against safe outputs and inspect the Spark SQL UI and
task metrics. A `count()` may have a different plan from a write.

## Polars

```python
import polars as pl

result = pipeline.run(context, include_side_effects=False)
frame = result.get_output("build_report", pl.LazyFrame)
print(frame.explain())
```

Inspect scan projections, pushed predicates, joins, and `CACHE` nodes. If the application
executes several lazy frames together with `pl.collect_all`, inspect them together with
`pl.explain_all(frames)`. Include lazy sink frames when those are what `collect_all` receives.
An individual `frame.explain()` cannot show sharing across frames. Pass the same
`optimizations=pl.QueryOptFlags(...)` to `explain_all` that the application passes to
`collect_all`; check the installed Polars API before using version-specific flags.

## Compare plans with measurements

Compare the same input, output boundary, backend version, and optimizer settings. Separate
planning or reader-validation time from execution time. Plans show proposed work, not its
cost: time the real action with temporary outputs when diagnosing performance, repeat
measurements to account for warm caches, and report both plan evidence and elapsed times.
Do not treat a cache, duplicated scan, or join strategy as inherently faster without
measuring the workload.
