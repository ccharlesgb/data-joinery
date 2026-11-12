"""Declarative command line jobs and runtime context lifetimes."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from data_joinery.pipeline import Pipeline


@contextmanager
def _resource_scope(manager: Any) -> Generator[Any]:
    context = manager.__enter__()
    try:
        yield context
    except BaseException:
        manager.__exit__(*sys.exc_info())
        raise
    else:
        manager.__exit__(None, None, None)


class Job[ContextT](typer.Typer):
    """Expose a pipeline as typed run and visualize commands.

    Args:
        pipeline: Constructed graph, without runtime resource acquisition.
        context_provider: Function accepting CLI inputs and returning the pipeline
            context, or a synchronous context manager yielding it. Omit for a
            context-free pipeline. Put runtime setup inside this function.
    """

    RUN_COMMAND_NAME = "run"
    VISUALIZE_COMMAND_NAME = "visualize"

    def __init__(
        self,
        *,
        pipeline: Pipeline[ContextT],
        context_provider: Callable[..., ContextT | AbstractContextManager[ContextT]]
        | None = None,
    ) -> None:
        super().__init__(help="Data Joinery CLI")
        self._pipeline = pipeline
        self._context_provider = context_provider
        self._validate_context_provider()
        self.command(name=self.RUN_COMMAND_NAME, help="Run the pipeline.")(
            self._build_run_command()
        )
        self.command(name=self.VISUALIZE_COMMAND_NAME, help="Visualize the pipeline.")(
            self._visualize
        )

    def _validate_context_provider(self) -> None:
        """Check that the provider matches the pipeline's context requirements."""
        context_provider = self._context_provider
        if context_provider is None and self._pipeline._context_type is not None:
            raise TypeError("This job requires a context_provider passed to Job().")
        if context_provider is not None:
            if self._pipeline._context_type is None:
                raise TypeError("A context-free pipeline cannot accept a provider.")
            original = inspect.unwrap(context_provider)
            if inspect.iscoroutinefunction(original) or inspect.isasyncgenfunction(
                original
            ):
                raise TypeError("Async context providers are not supported.")
            if inspect.isgeneratorfunction(context_provider):
                raise TypeError("Wrap generator providers with @contextmanager.")

    def _execute(self, **kwargs: Any) -> None:
        """Acquire runtime context and run the pipeline within its resource scope."""
        typer.echo("Running pipeline...")
        with ExitStack() as stack:
            if self._context_provider is None:
                cast(Pipeline[None], self._pipeline).run()
            else:
                context = self._context_provider(**kwargs)
                context_type = self._pipeline._context_type
                assert context_type is not None
                if not isinstance(context, context_type) and (
                    hasattr(type(context), "__enter__")
                    and hasattr(type(context), "__exit__")
                ):
                    context = stack.enter_context(_resource_scope(context))
                self._pipeline.run(cast(ContextT, context))
        typer.echo("Pipeline finished.")

    def _build_run_command(self) -> Callable[..., None]:
        """Build a CLI callback with the provider's signature, when present."""
        if self._context_provider is not None:

            @wraps(self._context_provider)
            def execute(**kwargs: Any) -> None:
                self._execute(**kwargs)

            return execute

        # Typer needs a parameterless command for a context-free job.
        def run() -> None:
            """Run the pipeline."""
            self._execute()

        return run

    def _visualize(
        self,
        output: Annotated[
            Path | None,
            typer.Option("--output", help="Save the diagram to an SVG or PNG file."),
        ] = None,
    ) -> None:
        """Display a pipeline diagram, or save it to a file."""
        if output is not None and output.suffix.lower() not in {".svg", ".png"}:
            raise typer.BadParameter("--output must end in .svg or .png.")
        typer.echo("Visualizing pipeline...")
        try:
            figure = self._pipeline.visualize(show=output is None)
        except ImportError as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(1) from error
        if output is not None:
            try:
                figure.savefig(output)
            finally:
                from matplotlib import pyplot as plt

                plt.close(figure)
            typer.echo(f"Pipeline visualization saved to {output}.")
        else:
            typer.echo("Pipeline visualization displayed.")
