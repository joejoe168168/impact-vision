"""Fold one agent tool into another without losing typed inputs (v7 W1.5).

``merge_tools(Target, Source, action_map)`` returns a tool class named like
*Target* whose input model is the union of both tools' fields. The source's
actions are added under new names (``action_map``: source action → merged
action) and dispatched to the original source implementation, so behaviour
is unchanged and the LLM still sees a typed schema.

Field collisions with the same type are shared; incompatible ones are exposed
under ``<rename_prefix><field>`` for the source. Source fields that were
required become optional in the merged schema and are validated when a
source action is called.
"""

from __future__ import annotations

import typing
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from impact_vision.tools.base import BaseTool, ToolExecutionContext, ToolResult


def _actions(model: type[BaseModel]) -> tuple[str, ...]:
    field = model.model_fields.get("action")
    return typing.get_args(field.annotation) if field is not None else ()


def _optional(info: FieldInfo) -> FieldInfo:
    if not info.is_required():
        return info
    return FieldInfo.merge_field_infos(info, default=None)


def merge_tools(
    target: type[BaseTool],
    source: type[BaseTool],
    action_map: dict[str, str],
    *,
    default_action: str | None = None,
    target_action_without_field: str = "",
    rename_prefix: str = "",
    summary: str = "",
) -> type[BaseTool]:
    """Return a tool class: *target* plus *source*'s actions (see module doc).

    ``target_action_without_field`` names the action that runs *target* when
    it had no ``action`` field (e.g. ``pitch_deck_analyze`` → ``"analyze"``).
    """
    t_model, s_model = target.input_model, source.input_model
    t_actions = _actions(t_model) or ((target_action_without_field,) if target_action_without_field else ())
    s_actions = _actions(s_model)
    missing = [a for a in s_actions if a not in action_map]
    if missing:
        raise ValueError(f"action_map misses source actions: {missing}")
    clashes = set(action_map.values()) & set(t_actions)
    if clashes:
        raise ValueError(f"merged action names clash with target actions: {sorted(clashes)}")

    fields: dict[str, tuple[Any, FieldInfo]] = {}
    for name, info in t_model.model_fields.items():
        if name != "action":
            fields[name] = (info.annotation, info)
    source_field_names: dict[str, str] = {}  # merged name -> source name
    for name, info in s_model.model_fields.items():
        if name == "action":
            continue
        merged_name = name
        if name in fields and fields[name][0] != info.annotation:
            merged_name = f"{rename_prefix}{name}"
        source_field_names[merged_name] = name
        if merged_name not in fields:
            fields[merged_name] = (info.annotation, _optional(info))

    all_actions = tuple(t_actions) + tuple(action_map[a] for a in s_actions)
    t_action_field = t_model.model_fields.get("action")
    if default_action is not None:
        action_default: Any = default_action
    elif t_action_field is not None and not t_action_field.is_required():
        action_default = t_action_field.default
    else:
        action_default = ...
    source_desc = ", ".join(f"'{action_map[a]}'" for a in s_actions)
    fields["action"] = (
        Literal[all_actions],  # type: ignore[valid-type]
        Field(
            default=action_default,
            description=(
                (t_action_field.description + " " if t_action_field and t_action_field.description else "")
                + f"Also {source_desc} ({summary or source.name})."
            ),
        ),
    )
    merged_model = create_model(t_model.__name__, __base__=BaseModel, **fields)  # type: ignore[call-overload]
    reverse = {v: k for k, v in action_map.items()}
    target_fields = set(t_model.model_fields)

    class Merged(BaseTool):
        name = target.name
        description = (
            f"{target.description} Also covers {summary or source.name} via action "
            f"{source_desc} (formerly the '{source.name}' tool)."
        )
        input_model = merged_model
        merged_from = (target.name, source.name)

        def __init__(self) -> None:
            self._target = target()
            self._source = source()

        def _split(self, args: BaseModel) -> tuple[BaseTool, BaseModel]:
            data = args.model_dump(exclude_unset=True)
            action = getattr(args, "action", None)
            if action in reverse:
                payload = {
                    source_field_names[k]: v for k, v in data.items() if k in source_field_names
                }
                payload["action"] = reverse[action]
                return self._source, s_model.model_validate(payload)
            payload = {k: v for k, v in data.items() if k in target_fields and k != "action"}
            if "action" in target_fields:
                payload["action"] = action
            return self._target, t_model.model_validate(payload)

        def _coerce(self, arguments: BaseModel) -> BaseModel:
            return arguments if isinstance(arguments, merged_model) else merged_model.model_validate(
                arguments.model_dump() if isinstance(arguments, BaseModel) else arguments
            )

        def is_read_only(self, arguments: BaseModel) -> bool:
            try:
                tool, args = self._split(self._coerce(arguments))
            except Exception:  # noqa: BLE001 - validation errors surface in execute
                return False
            return tool.is_read_only(args)

        async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
            try:
                tool, args = self._split(self._coerce(arguments))
            except Exception as exc:  # noqa: BLE001 - report as a tool error
                return ToolResult(output=f"Invalid input: {exc}", is_error=True)
            return await tool.execute(args, context)

    Merged.__name__ = target.__name__
    Merged.__qualname__ = target.__name__
    return Merged


def deprecated_alias(tool_cls: type[BaseTool], replacement: str) -> type[BaseTool]:
    """Keep an old tool name working for one release, flagged as deprecated."""

    class Deprecated(tool_cls):  # type: ignore[valid-type, misc]
        description = f"[Deprecated: use {replacement}] {tool_cls.description}"
        deprecated_for = replacement

    Deprecated.__name__ = tool_cls.__name__
    Deprecated.__qualname__ = tool_cls.__name__
    return Deprecated


__all__ = ["deprecated_alias", "merge_tools"]
