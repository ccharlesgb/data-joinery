"""Declarative command line jobs and runtime context lifetimes."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Annotated, Any, TypeVar, cast, get_type_hints

import typer
from typer.main import get_click_param, get_params_from_function

from data_joinery.pipeline import Pipeline

ProviderT = TypeVar("ProviderT", bound=Callable[..., Any])


@contextmanager
def _resource_scope(manager: Any) -> Iterator[Any]:
    context = manager.__enter__()
    try:
        yield context
    except BaseException:
        manager.__exit__(*sys.exc_info())
        raise
    else:
        manager.__exit__(None, None, None)


def _provider_signature(provider: Callable[..., Any]) -> inspect.Signature:
    original = inspect.unwrap(provider)
    name = getattr(provider, "__qualname__", repr(provider))
    if inspect.iscoroutinefunction(original) or inspect.isasyncgenfunction(original):
        raise TypeError(f"Provider {name}: async providers are not supported.")
    if inspect.isgeneratorfunction(provider):
        raise TypeError(
            f"Provider {name}: wrap generator providers with @contextmanager."
        )
    signature = inspect.signature(provider)
    hints = get_type_hints(original, include_extras=True)
    parameters = []
    for parameter in signature.parameters.values():
        if parameter.kind not in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }:
            raise TypeError(
                f"Provider {name}: unsupported parameter '{parameter.name}'."
            )
        if parameter.name == "skip_side_effects":
            raise ValueError(
                f"Provider {name}: parameter 'skip_side_effects' is reserved."
            )
        parameters.append(
            parameter.replace(
                annotation=hints.get(parameter.name, parameter.annotation)
            )
        )
    return signature.replace(parameters=parameters, return_annotation=None)


def _check_options(adapter: Callable[..., Any], provider: Callable[..., Any]) -> None:
    for name, parameter in get_params_from_function(adapter).items():
        option, _ = get_click_param(parameter)
        aliases = [*option.opts, *getattr(option, "secondary_opts", [])]
        if any(alias in {"--skip-side-effects", "--help"} for alias in aliases):
            raise ValueError(
                f"Provider {provider.__qualname__}: parameter '{name}' uses a reserved "
                "option (--skip-side-effects or --help)."
            )


class Job[ContextT]:
    """Expose a pipeline as typed run and visualize commands.

    Args:
        pipeline: Constructed graph. Acquire runtime resources inside a provider
            registered with :meth:`context`.
    """

    def __init__(self, *, pipeline: Pipeline[ContextT]) -> None:
        self.pipeline = pipeline
        self._provider: Callable[..., Any] | None = None
        self._signature: inspect.Signature | None = None
        self._app: typer.Typer | None = None

    def context(self) -> Callable[[ProviderT], ProviderT]:
        """Register one plain or synchronous context manager provider.

        Returns:
            A decorator that leaves the provider independently callable.

        Raises:
            TypeError: If the provider signature or pipeline context is unsupported.
            ValueError: If registration is duplicate, late, or uses reserved options.
        """

        def register(provider: ProviderT) -> ProviderT:
            name = getattr(provider, "__qualname__", repr(provider))
            if self._app is not None:
                raise ValueError(
                    f"Provider {name}: job commands are already finalized."
                )
            if self._provider is not None:
                raise ValueError(
                    f"Provider {name}: a context provider is already registered."
                )
            if self.pipeline._context_type is None:
                raise TypeError(
                    f"Provider {name}: a context-free pipeline cannot register a provider."
                )
            signature = _provider_signature(provider)

            def probe(**kwargs: Any) -> None:
                pass

            probe.__signature__ = signature  # type: ignore[missing-attribute]
            _check_options(probe, provider)
            self._signature = signature
            self._provider = provider
            return provider

        return register

    @property
    def app(self) -> typer.Typer:
        """Return the Typer application, finalizing its commands on first access."""
        if self._app is None:
            app = typer.Typer(help="Run and visualize a Data Joinery pipeline.")

            @app.callback()
            def root() -> None:
                pass

            def run(**inputs: Any) -> None:
                skip = inputs.pop("skip_side_effects")
                typer.echo("Running pipeline...")
                with ExitStack() as stack:
                    if self._provider is None:
                        if self.pipeline._context_type is not None:
                            raise TypeError(
                                "This job requires a context provider; register one with @job.context()."
                            )
                        cast(Pipeline[None], self.pipeline).run(
                            include_side_effects=not skip
                        )
                    else:
                        context = self._provider(**inputs)
                        context_type = self.pipeline._context_type
                        assert context_type is not None
                        if not isinstance(context, context_type) and (
                            hasattr(type(context), "__enter__")
                            and hasattr(type(context), "__exit__")
                        ):
                            context = stack.enter_context(_resource_scope(context))
                        self.pipeline.run(context, include_side_effects=not skip)
                typer.echo("Pipeline finished.")

            parameters = (
                list(self._signature.parameters.values()) if self._signature else []
            )
            parameters.append(
                inspect.Parameter(
                    "skip_side_effects",
                    inspect.Parameter.KEYWORD_ONLY,
                    default=False,
                    annotation=Annotated[
                        bool,
                        typer.Option(
                            "--skip-side-effects", help="Skip marked side effect steps."
                        ),
                    ],
                )
            )
            run.__signature__ = inspect.Signature(parameters, return_annotation=None)  # type: ignore[missing-attribute]
            run.__doc__ = (
                self._provider.__doc__ if self._provider else "Run the pipeline."
            )
            app.command()(run)
            app.command("visualize")(self._visualize)
            self._app = app
        return self._app

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke Typer, optionally passing an explicit ``args`` list.

        Args:
            *args: Positional arguments forwarded to Typer.
            **kwargs: Keyword arguments forwarded to Typer.

        Returns:
            Typer's invocation result.
        """
        return self.app(*args, **kwargs)

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
            figure = self.pipeline.visualize(show=output is None)
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
