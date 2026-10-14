set shell := ["zsh", "-cu"]

default:
    just --list

install:
    uv sync --all-extras --all-groups

test:
    uv run --extra all pytest --ignore=docs_src/

test-compat service:
    docker compose run --build --rm {{service}}

test-matrix:
    docker compose build
    docker compose run --rm dbr17-polars1
    docker compose run --rm dbr17-polars2
    docker compose run --rm dbr18-polars1
    docker compose run --rm dbr18-polars2

lint-code:
    uv run ruff check . --fix

lint-deps:
    uv run deptry src

lint-types:
    uv run --extra all pyrefly check

lint-format:
    uv run ruff format .

lint: lint-deps lint-code lint-types lint-format

check: lint test

agent-clear-test-report:
    rm -f test-report.xml

agent-lint-code:
    uv run ruff check . --fix --output-format concise

agent-test: agent-clear-test-report
    uv run --extra all pytest --ignore=docs_src/ --tb=short --junitxml=test-report.xml

agent-lint: lint-deps agent-lint-code lint-types lint-format

agent-check: agent-lint agent-test

docs-serve: docs-examples
    uv run --extra all zensical build --clean
    uv run --extra all zensical serve

docs-build: docs-examples
    uv run --extra all zensical build --clean

docs-examples:
    uv run --extra all python scripts/run_docs_examples.py

docs-images:
    uv run --extra all python scripts/render_docs_pipeline.py

pipeline-gallery:
    uv run --extra all python scripts/render_pipeline_gallery.py

typos:
    typos
