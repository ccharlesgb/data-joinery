set shell := ["zsh", "-cu"]

default:
    just --list

install:
    uv sync --all-extras --all-groups

run:
    uv run data-joinery

test:
    uv run pytest --ignore=docs_src/

lint-code:
    uv run ruff check . --fix

lint-deps:
    uv run deptry src

lint-types:
    uv run pyrefly check

lint-format:
    uv run ruff format .

lint: lint-deps lint-code lint-types lint-format

check: lint test

agent-clear-test-report:
    rm -f test-report.xml

agent-lint-code:
    uv run ruff check . --fix --output-format concise

agent-test: agent-clear-test-report
    uv run pytest --ignore=docs_src/ --tb=short --junitxml=test-report.xml

agent-lint: lint-deps agent-lint-code lint-types lint-format

agent-check: agent-lint agent-test

docs-serve:
    uv run zensical build --clean
    uv run zensical serve

docs-build:
    uv run zensical build --clean

docs-examples:
    uv run python scripts/run_docs_examples.py

typos:
    typos