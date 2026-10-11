"""Command line entry point for running and drawing pipelines."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer

from data_joinery.pipeline import Pipeline

app = typer.Typer(help="Run and visualize Data Joinery pipelines.")


def _error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


def _load_pipeline(target: str) -> Pipeline[Any]:
    location, separator, attribute = target.partition(":")
    if separator and not attribute:
        _error("A pipeline name is required after ':'.")

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

    names = (attribute,) if separator else ("pipeline", "build_pipeline")
    for name in names:
        if not hasattr(module, name):
            continue
        value = getattr(module, name)
        try:
            pipeline = value() if callable(value) else value
        except (TypeError, ValueError, RuntimeError) as error:
            _error(f"Cannot build pipeline '{name}': {error}")
        if not isinstance(pipeline, Pipeline):
            _error(f"'{name}' in {location} is not a Pipeline.")
        return pipeline
    _error(f"No pipeline found in {location}; expected " + ", ".join(names) + ".")


def _build_context(pipeline: Pipeline[Any], values: list[str]) -> Any:
    context_type = pipeline._context_type
    if context_type is None:
        if values:
            _error("This pipeline has no context; remove --context.")
        return None

    kwargs: dict[str, str] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key:
            _error("--context values must use NAME=VALUE.")
        if key in kwargs:
            _error(f"Duplicate context value: {key}")
        kwargs[key] = raw

    factory = getattr(context_type, "from_kwargs", None)
    if factory is None and kwargs:
        _error(
            f"{context_type.__name__} must define from_kwargs(**values) "
            "to accept --context values."
        )
    try:
        context = factory(**kwargs) if factory is not None else context_type()
    except (TypeError, ValueError) as error:
        _error(f"Cannot create {context_type.__name__}: {error}")
    if not isinstance(context, context_type):
        _error(
            f"{context_type.__name__}.from_kwargs() must return a "
            f"{context_type.__name__} instance."
        )
    return context


@app.command()
def run(
    target: Annotated[
        str,
        typer.Argument(
            help="Python file or module, optionally followed by :attribute."
        ),
    ] = "main.py",
    context: Annotated[
        list[str] | None,
        typer.Option("--context", help="Context value as NAME=VALUE; may be repeated."),
    ] = None,
    skip_side_effects: Annotated[
        bool, typer.Option("--skip-side-effects", help="Skip marked side effect steps.")
    ] = False,
) -> None:
    """Run a pipeline and its steps in dependency order."""
    pipeline = _load_pipeline(target)
    pipeline.run(
        _build_context(pipeline, context or []),
        include_side_effects=not skip_side_effects,
    )


@app.command()
def visualize(
    target: Annotated[
        str,
        typer.Argument(
            help="Python file or module, optionally followed by :attribute."
        ),
    ] = "main.py",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Save the diagram to an SVG or PNG file."),
    ] = None,
) -> None:
    """Display a pipeline diagram, or save it to a file."""
    if output is not None and output.suffix.lower() not in {".svg", ".png"}:
        _error("--output must end in .svg or .png.")
    pipeline = _load_pipeline(target)
    try:
        figure = pipeline.visualize(show=output is None)
    except ImportError as error:
        _error(str(error))
    if output is not None:
        try:
            figure.savefig(output)
        except OSError as error:
            _error(f"Cannot save {output}: {error}")
        finally:
            from matplotlib import pyplot as plt

            plt.close(figure)


if __name__ == "__main__":
    app()
