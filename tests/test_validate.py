import dataclasses
import pytest
from violetear.validate import signature_to_model, js_check_spec, js_return_check


def _fn(message: str, color: str): ...
def _nums(count: int, ratio: float, flag: bool): ...
def _containers(tags: list[str], scores: dict[str, int]): ...
def _optional(note: str | None): ...
def _untyped(whatever): ...
def _skips(client_id: str, msg: str): ...


def test_js_check_spec_primitives():
    assert js_check_spec(_fn) == "{ message: _checkStr, color: _checkStr }"


def test_js_check_spec_numeric_and_bool():
    assert (
        js_check_spec(_nums)
        == "{ count: _checkInt, ratio: _checkNumber, flag: _checkBool }"
    )


def test_js_check_spec_containers():
    assert js_check_spec(_containers) == (
        "{ tags: (v, p) => _checkList(v, p, _checkStr), "
        "scores: (v, p) => _checkDict(v, p, _checkInt) }"
    )


def test_js_check_spec_optional():
    assert (
        js_check_spec(_optional)
        == "{ note: (v, p) => _checkOptional(v, p, _checkStr) }"
    )


def _bare_containers(msg: dict, items: list): ...


def test_js_check_spec_bare_containers():
    # `msg: dict` / `items: list` (no type params) — check container kind only.
    assert js_check_spec(_bare_containers) == (
        "{ msg: (v, p) => _checkDict(v, p, _checkAny), "
        "items: (v, p) => _checkList(v, p, _checkAny) }"
    )


def test_js_check_spec_resolves_pep563_string_annotations():
    # Simulate `from __future__ import annotations`: annotations are strings.
    def _stringy(msg, count): ...

    _stringy.__annotations__ = {"msg": "dict", "count": "int"}
    assert js_check_spec(_stringy) == (
        "{ msg: (v, p) => _checkDict(v, p, _checkAny), count: _checkInt }"
    )


def test_js_check_spec_untyped_is_passthrough():
    assert js_check_spec(_untyped) == "{ whatever: _checkAny }"


def test_js_check_spec_skips_client_id():
    assert js_check_spec(_skips) == "{ msg: _checkStr }"


def test_signature_to_model_validates_and_rejects():
    Model = signature_to_model(_fn, "FnKwargs")
    assert Model(message="hi", color="green").model_dump() == {
        "message": "hi",
        "color": "green",
    }
    with pytest.raises(Exception):
        Model(message="hi", color=123)


def test_signature_to_model_empty_params_ok():
    def _noargs(): ...

    Model = signature_to_model(_noargs, "NoArgsKwargs")
    assert Model().model_dump() == {}


def _ret_dict(x: int) -> dict: ...
def _ret_none(x: int) -> None: ...
def _ret_untyped(x: int): ...
def _ret_str(x: int) -> str: ...


def test_js_return_check_dict():
    assert js_return_check(_ret_dict) == "(v, p) => _checkDict(v, p, _checkAny)"


def test_js_return_check_str():
    assert js_return_check(_ret_str) == "_checkStr"


def test_js_return_check_none_is_any():
    assert js_return_check(_ret_none) == "_checkAny"


def test_js_return_check_untyped_is_any():
    assert js_return_check(_ret_untyped) == "_checkAny"
