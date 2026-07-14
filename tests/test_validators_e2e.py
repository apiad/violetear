"""Exercise the runtime.js validator primitives in a real JS engine (Chromium)
via Playwright. Marked e2e because it needs a browser. This closes the
'pure-JS runtime path is untested' gap (AGENTS.md) for the validator library.

We navigate to a canonical example (real HTTP origin, runtime.js loaded as
globals) rather than injecting runtime.js into about:blank — runtime.js touches
window.localStorage at load, which throws on an opaque origin.
"""

import pytest

HYDRATION_TIMEOUT_MS = 45_000


def _boot(example_server, page):
    base = example_server("03_interactive.py")
    page.goto(base + "/")
    # runtime.js is loaded before the bundle; cloak removal (end of bundle eval)
    # guarantees the runtime globals exist.
    page.wait_for_function(
        "() => document.getElementById('violetear-cloak') === null",
        timeout=HYDRATION_TIMEOUT_MS,
    )


@pytest.mark.e2e
def test_validate_kwargs_accepts_valid(example_server, page):
    _boot(example_server, page)
    ok = page.evaluate(
        "() => { _validateKwargs('update_alert', {message:'hi', color:'green'}, "
        "{message:_checkStr, color:_checkStr}); return true; }"
    )
    assert ok is True


@pytest.mark.e2e
def test_validate_kwargs_rejects_wrong_type_naming_field(example_server, page):
    _boot(example_server, page)
    err = page.evaluate(
        "() => { try { _validateKwargs('update_alert', {message:'hi', color:123}, "
        "{message:_checkStr, color:_checkStr}); return null; } "
        "catch (e) { return e.message; } }"
    )
    assert err is not None
    assert "update_alert.color" in err


@pytest.mark.e2e
def test_check_int_rejects_float(example_server, page):
    _boot(example_server, page)
    err = page.evaluate(
        "() => { try { _checkInt(1.5, 'x.n'); return null; } catch (e) { return e.message; } }"
    )
    assert err is not None and "x.n" in err


@pytest.mark.e2e
def test_check_list_and_optional(example_server, page):
    _boot(example_server, page)
    err = page.evaluate(
        "() => { try { _checkList(['a', 2], 'x.tags', _checkStr); return null; } "
        "catch (e) { return e.message; } }"
    )
    assert err is not None and "x.tags[1]" in err
    ok = page.evaluate(
        "() => { _checkOptional(null, 'x.note', _checkStr); return true; }"
    )
    assert ok is True
