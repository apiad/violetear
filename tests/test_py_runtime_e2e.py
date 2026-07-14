"""Exercise the runtime.js _py semantics helper in Chromium via Playwright.
Marked e2e (needs a browser); runs on a browser-equipped host. Navigates a
canonical example (runtime.js loaded as globals) rather than about:blank."""

import pytest

HYDRATION_TIMEOUT_MS = 45_000


def _boot(example_server, page):
    base = example_server("03_interactive.py")
    page.goto(base + "/")
    page.wait_for_function(
        "() => document.getElementById('violetear-cloak') === null",
        timeout=HYDRATION_TIMEOUT_MS,
    )


@pytest.mark.e2e
def test_py_truthy(example_server, page):
    _boot(example_server, page)
    assert page.evaluate(
        "() => [_py.truthy([]), _py.truthy([1]), _py.truthy(0), "
        "_py.truthy(''), _py.truthy({}), _py.truthy({a:1}), _py.truthy(false)]"
    ) == [False, True, False, False, False, True, False]


@pytest.mark.e2e
def test_py_eq_and_shortcircuit(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.eq([1,2],[1,2])") is True
    assert page.evaluate("() => _py.eq({a:1},{a:1})") is True
    assert page.evaluate("() => _py.eq([1],[2])") is False
    assert page.evaluate("() => _py.or([], () => 5)") == 5
    assert page.evaluate("() => _py.and([1], () => 2)") == 2


@pytest.mark.e2e
def test_py_format(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.format(5, '02d')") == "05"
    assert page.evaluate("() => _py.format(3.14159, '.2f')") == "3.14"
    assert page.evaluate("() => _py.format(255, 'x')") == "ff"
