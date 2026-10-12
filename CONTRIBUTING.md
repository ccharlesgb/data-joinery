## Development

This project uses `uv` for Python/dependency management and `just` as the command runner.

### Quick start

```bash
just install
```

### Common commands

```bash
just test
just lint
just format
just check
```

### Backend compatibility tests

Run `just test` locally with your installed JDK and the dependencies from `uv.lock`.
To reproduce one CI cell, use `just test-compat dbr17-polars1` (or another service
from `compose.yaml`). Run all four with `just test-matrix`. These commands need Docker.

The same Compose services run after pushes to `main` in GitHub Actions. They cross
the Databricks Runtime 17.3 LTS and 18 LTS base images with the latest Polars 1 and 2
releases. The images supply Linux, Python, and JDK; each container installs bounded
open source PySpark in a virtual environment to run local Spark tests. The `dev`
dependency group in `pyproject.toml` supplies the test tools in both development
and Docker. The Polars compatibility runtime also supports running the x86 images
on ARM Docker hosts.
These containers do not start a Databricks cluster or test Databricks-specific
Spark behavior.

The LTS image tags receive patches, and the Polars and PySpark ranges can select newer
patch releases. The jobs print the versions they import so failures can be reproduced.
If you need fresh versions after a local image was built, run
`docker compose build --pull --no-cache dbr17-polars1` before that service.
Update the image tags and Spark ranges when Databricks publishes another LTS runtime.

See the [Databricks Runtime version table](https://docs.databricks.com/aws/en/release-notes/runtime/)
and [Polars release history](https://pypi.org/project/polars/#history) when updating the
matrix.
