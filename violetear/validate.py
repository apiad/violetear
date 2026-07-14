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
    # eval_str resolves PEP 563 string annotations (`from __future__ import
    # annotations` turns `dict` into the string "dict"); without it every
    # annotation degrades to a bare string and validation is lost.
    sig = inspect.signature(inspect.unwrap(func), eval_str=True)
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

    # Bare, unparametrized containers (`dict`, `list`) — check the container
    # kind, elements unchecked.
    if annotation is list:
        return "(v, p) => _checkList(v, p, _checkAny)"
    if annotation is dict:
        return "(v, p) => _checkDict(v, p, _checkAny)"

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
    sig = inspect.signature(inspect.unwrap(func), eval_str=True)
    entries: list[str] = []
    for name, param in sig.parameters.items():
        if name in _SKIP_PARAMS:
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = Any
        entries.append(f"{name}: {_js_checker(annotation)}")
    return "{ " + ", ".join(entries) + " }"


def js_type_check(annotation: Any) -> str:
    """Public: JS check expression for an already-resolved type annotation."""
    if annotation is None:
        return "_checkAny"
    return _js_checker(annotation)


def js_return_check(func: Callable) -> str:
    """Return a single JS check expression for a function's return annotation."""
    sig = inspect.signature(inspect.unwrap(func), eval_str=True)
    ann = sig.return_annotation
    if ann is inspect.Signature.empty or ann is type(None):
        return "_checkAny"
    return _js_checker(ann)
