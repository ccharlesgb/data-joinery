set shell := ["zsh", "-cu"]

default:
    just --list

install:
    uv sync --all-extras --all-groups

run:
    uv run data-joinery

test:
    uv run pytest --ignore=docs_src/

lint:
    uv run ruff check . --fix

dep-lint:
    uv run deptry src

types:
    uv run pyrefly check

format:
    uv run ruff format .

check: dep-lint lint types format test

docs-serve:
    uv run zensical build --clean
    uv run zensical serve

docs-build:
    uv run zensical build --clean

docs-examples:
    uv run python scripts/run_docs_examples.py

typos:
    typos