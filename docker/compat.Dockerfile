ARG DATABRICKS_IMAGE=databricksruntime/standard:17.3-LTS
FROM ${DATABRICKS_IMAGE}

ARG PYSPARK_REQUIREMENT
ARG POLARS_REQUIREMENT

WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY src/ src/

RUN /databricks/python3/bin/python -m pip install 'uv>=0.9.27,<0.10'
RUN /databricks/python3/bin/uv venv /opt/data-joinery-venv \
    --python /databricks/python3/bin/python
RUN --mount=type=cache,target=/root/.cache/uv \
    /databricks/python3/bin/uv pip install --link-mode=copy \
    --python /opt/data-joinery-venv/bin/python \
    --group dev -e '.[all]' \
    "$PYSPARK_REQUIREMENT" "$POLARS_REQUIREMENT"

COPY tests/ tests/
COPY scripts/run_compat_tests.py scripts/run_compat_tests.py

ENV SPARK_LOCAL_IP=127.0.0.1 \
    PYARROW_IGNORE_TIMEZONE=1

ENTRYPOINT ["/opt/data-joinery-venv/bin/python", "scripts/run_compat_tests.py"]
