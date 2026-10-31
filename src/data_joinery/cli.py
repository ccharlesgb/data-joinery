"""Load jobs and delegate command line inputs to their Typer applications."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn

import typer

from data_joinery.job import Job

app = typer.Typer(help="Run and visualize Data Joinery jobs.")


def _error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


def _import_target(location: str) -> ModuleType:
    path: Path | None = None
    if location.endswith(".py") or "/" in location or "\\" in location:
        path = Path(location).resolve()
        if not path.is_file() or path.suffix != ".py":
            _error(f"Python file does not exist: {location}")
        package_parts = [path.stem]
        root = path.parent
        while (root / "__init__.py").is_file():
            package_parts.insert(0, root.name)
            root = root.parent
        package_name = ".".join(package_parts[:-1])
        unique_name = f"_data_joinery_cli_{abs(hash(path))}"
        module_name = f"{package_name}.{unique_name}" if package_name else unique_name
        import_root = str(root)
    else:
        module_name = location
        import_root = None

    try:
        if import_root is not None and import_root not in sys.path:
            sys.path.insert(0, import_root)
        if import_root is None:
            module = importlib.import_module(module_name)
        else:
            assert path is not None
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                _error(f"Cannot load Python file: {location}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                del sys.modules[module_name]
                raise
    except (ImportError, SyntaxError) as error:
        _error(f"Cannot import {location}: {error}")

    return module


def _load_job(target: str) -> Job[Any]:
    location, separator, attribute = target.partition(":")
    if separator and not attribute:
        _error("A job name is required after ':'.")
    module = _import_target(location)

    names = (attribute,) if separator else ("job", "build_job")
    for name in names:
        if not hasattr(module, name):
            continue
        value = getattr(module, name)
        try:
            if isinstance(value, Job):
                return value
            job = value() if callable(value) else value
        except (TypeError, ValueError, RuntimeError) as error:
            _error(f"Cannot build job '{name}': {error}")
        if not isinstance(job, Job):
            _error(f"'{name}' in {location} is not a Job.")
        return job
    _error(f"No job found in {location}; expected " + ", ".join(names) + ".")


def _delegate(command: str, context: typer.Context) -> None:
    # Parse only the target here; the job owns all application inputs and help.
    remaining = list(context.args)
    if remaining and remaining[0] == "--help":
        typer.echo(context.get_help())
        return
    target = (
        remaining.pop(0)
        if remaining and not remaining[0].startswith("-")
        else "main.py"
    )
    job = _load_job(target)
    job(args=[command, *remaining], prog_name=f"data-joinery {target}")


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    },
)
def run(context: typer.Context) -> None:
    """Run a job: run [TARGET] [COMMAND_INPUTS...].

    TARGET is a Python file or module, optionally followed by :attribute.
    It defaults to main.py. Put the target before application inputs.
    """
    _delegate("run", context)


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    },
)
def visualize(context: typer.Context) -> None:
    """Draw a job: visualize [TARGET] [--output diagram.svg]."""
    _delegate("visualize", context)


if __name__ == "__main__":
    app()
