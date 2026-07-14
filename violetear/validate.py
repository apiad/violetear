"""Derive validators from a function signature — one source, both sides.

signature_to_model → a Pydantic model for server-side validation (reuses the
same create_model path App._register_rpc_route already uses for RPC bodies).
js_check_spec → a JS object-literal string of _check* expressions for the
client-side validator emitted into the bundle. Both read the identical
signature, so the two sides cannot drift.
"""

from __future__ import annotations

import dataclasses
import inspect
import types
from typing import Any, Callable, Union, get_args, get_origin

from pydantic import BaseModel, create_model

_SKIP_PARAMS = {"self", "client_id"}

_PRIMITIVE_CHECKS: dict[type, str] = {
    int: "_checkInt",
    float: "_checkNumber",
    str: "_checkStr",
    bool: "_checkBool",
}


def signature_to_model(func: Callable, model_name: str) -> type[BaseModel]:
    """Build a Pydantic model from a function's typed parameters."""
    sig = inspect.signature(inspect.unwrap(func))
    fields: dict[str, tuple] = {}
    for name, param in sig.parameters.items():
        if name in _SKIP_PARAMS:
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = Any
        default = param.default
        if default is inspect.Parameter.empty:
            default = ...
        fields[name] = (annotation, default)
    return create_model(model_name, **fields)


def _js_checker(annotation: Any) -> str:
    """Return a JS check expression for one annotation (pass-through if unsupported)."""
    if annotation in _PRIMITIVE_CHECKS:
        return _PRIMITIVE_CHECKS[annotation]

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if len(args) == 2 and len(non_none) == 1:
            return f"(v, p) => _checkOptional(v, p, {_js_checker(non_none[0])})"
        return "_checkAny"

    if origin is list:
        elem = _js_checker(args[0]) if args else "_checkAny"
        return f"(v, p) => _checkList(v, p, {elem})"

    if origin is dict:
        val = _js_checker(args[1]) if len(args) == 2 else "_checkAny"
        return f"(v, p) => _checkDict(v, p, {val})"

    if dataclasses.is_dataclass(annotation):
        parts = [
            f"{f.name}: {_js_checker(f.type)}" for f in dataclasses.fields(annotation)
        ]
        return f"(v, p) => _checkShape(v, p, {{{', '.join(parts)}}})"

    return "_checkAny"


def js_check_spec(func: Callable) -> str:
    """Return a JS object literal `{ name: <checker>, ... }` for a signature."""
    sig = inspect.signature(inspect.unwrap(func))
    entries: list[str] = []
    for name, param in sig.parameters.items():
        if name in _SKIP_PARAMS:
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = Any
        entries.append(f"{name}: {_js_checker(annotation)}")
    return "{ " + ", ".join(entries) + " }"
