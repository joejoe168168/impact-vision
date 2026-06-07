"""Compatibility shims for upstream MCP dependency changes."""

from __future__ import annotations

from typing import Any, Annotated, get_args, get_origin

from pydantic import BaseModel, Field, WithJsonSchema, create_model


def patch_fastmcp_func_metadata() -> None:
    """Patch FastMCP argument model creation for newer Pydantic releases.

    Some FastMCP versions pass ``Annotated[...]`` as a bare value to
    ``pydantic.create_model`` for required parameters. Pydantic 2.12 rejects
    that shape as a non-annotated attribute. Building each field as
    ``(annotation, Field(...))`` keeps the generated schemas equivalent while
    remaining accepted by Pydantic.
    """
    patch_anyio_memory_stream_subscript()
    try:
        import inspect

        from mcp.server.fastmcp.resources import templates as resource_templates
        from mcp.server.fastmcp.tools import base as tool_base
        from mcp.server.fastmcp.utilities import func_metadata as fm
        from mcp.types import CallToolResult
    except Exception:  # pragma: no cover
        return

    if getattr(fm, "_openharness_patched", False):
        return

    def compat_create_wrapped_model(func_name: str, annotation: Any) -> type[BaseModel]:
        return create_model(f"{func_name}Output", result=(annotation, ...))

    def compat_func_metadata(
        func: Any,
        skip_names: Any = (),
        structured_output: bool | None = None,
    ) -> Any:
        try:
            sig = inspect.signature(func, eval_str=True)
        except NameError as exc:  # pragma: no cover
            raise fm.InvalidSignature(
                f"Unable to evaluate type annotations for callable {func.__name__!r}"
            ) from exc

        dynamic_pydantic_model_params: dict[str, Any] = {}
        for param in sig.parameters.values():
            if param.name.startswith("_"):  # pragma: no cover
                raise fm.InvalidSignature(
                    f"Parameter {param.name} of {func.__name__} cannot start with '_'"
                )
            if param.name in skip_names:
                continue

            annotation = param.annotation if param.annotation is not inspect.Parameter.empty else Any
            field_name = param.name
            field_kwargs: dict[str, Any] = {}
            field_metadata: list[Any] = []
            if param.annotation is inspect.Parameter.empty:
                field_metadata.append(WithJsonSchema({"title": param.name, "type": "string"}))
            if hasattr(BaseModel, field_name) and callable(getattr(BaseModel, field_name)):
                field_kwargs["alias"] = field_name
                field_name = f"field_{field_name}"

            annotated = Annotated[(annotation, *field_metadata)] if field_metadata else annotation
            if param.default is inspect.Parameter.empty:
                dynamic_pydantic_model_params[field_name] = (annotated, Field(..., **field_kwargs))
            else:
                dynamic_pydantic_model_params[field_name] = (
                    annotated,
                    Field(param.default, **field_kwargs),
                )

        arguments_model = create_model(
            f"{func.__name__}Arguments",
            __base__=fm.ArgModelBase,
            **dynamic_pydantic_model_params,
        )

        if structured_output is not True:
            return fm.FuncMetadata(arg_model=arguments_model)

        if sig.return_annotation is inspect.Parameter.empty and structured_output is True:
            raise fm.InvalidSignature(
                f"Function {func.__name__}: return annotation required for structured output"
            )

        try:
            inspected_return_ann = fm.inspect_annotation(
                sig.return_annotation,
                annotation_source=fm.AnnotationSource.FUNCTION,
            )
        except fm.ForbiddenQualifier as exc:
            raise fm.InvalidSignature(
                f"Function {func.__name__}: return annotation contains an invalid type qualifier"
            ) from exc

        return_type_expr = inspected_return_ann.type
        assert return_type_expr is not fm.UNKNOWN

        if fm.is_union_origin(get_origin(return_type_expr)):
            args = get_args(return_type_expr)
            if any(
                isinstance(arg, type) and issubclass(arg, CallToolResult)
                for arg in args
                if arg is not type(None)
            ):
                raise fm.InvalidSignature(
                    f"Function {func.__name__}: CallToolResult cannot be used in Union or Optional types. "
                    "To return empty results, use: CallToolResult(content=[])"
                )

        if isinstance(return_type_expr, type) and issubclass(return_type_expr, CallToolResult):
            if inspected_return_ann.metadata:
                return_type_expr = inspected_return_ann.metadata[0]
                if len(inspected_return_ann.metadata) >= 2:
                    original_annotation: Any = Annotated[
                        (return_type_expr, *inspected_return_ann.metadata[1:])
                    ]
                else:
                    original_annotation = return_type_expr
            else:
                return fm.FuncMetadata(arg_model=arguments_model)
        else:
            original_annotation = sig.return_annotation

        output_model, output_schema, wrap_output = fm._try_create_model_and_schema(
            original_annotation,
            return_type_expr,
            func.__name__,
        )
        if output_model is None and structured_output is True:
            raise fm.InvalidSignature(
                f"Function {func.__name__}: return type {return_type_expr} is not serializable for structured output"
            )
        return fm.FuncMetadata(
            arg_model=arguments_model,
            output_schema=output_schema,
            output_model=output_model,
            wrap_output=wrap_output,
        )

    fm.func_metadata = compat_func_metadata
    fm._create_wrapped_model = compat_create_wrapped_model
    tool_base.func_metadata = compat_func_metadata
    resource_templates.func_metadata = compat_func_metadata
    fm._openharness_patched = True


def patch_anyio_memory_stream_subscript() -> None:
    """Allow MCP code written for AnyIO 4 generics to run on AnyIO 3."""
    try:
        import anyio
    except Exception:  # pragma: no cover
        return

    create_stream = anyio.create_memory_object_stream
    if hasattr(create_stream, "__getitem__") or getattr(create_stream, "_openharness_patched", False):
        return

    class _SubscriptableCreateMemoryObjectStream:
        def __init__(self, wrapped: Any) -> None:
            self._wrapped = wrapped
            self._openharness_patched = True

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self._wrapped(*args, **kwargs)

        def __getitem__(self, item_type: Any) -> Any:
            def _factory(*args: Any, **kwargs: Any) -> Any:
                if "item_type" not in kwargs:
                    kwargs["item_type"] = item_type
                return self._wrapped(*args, **kwargs)

            return _factory

    anyio.create_memory_object_stream = _SubscriptableCreateMemoryObjectStream(create_stream)


__all__ = ["patch_anyio_memory_stream_subscript", "patch_fastmcp_func_metadata"]
