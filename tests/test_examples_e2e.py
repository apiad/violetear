"""
End-to-end tests — drive a real headless Chromium against a real uvicorn
server. Each test boots one canonical example, navigates to it, and asserts on
the browser-observable state after Pyodide finishes hydrating.

Marked `e2e` so the fast unit gate skips them. Run with:

    uv run pytest -m e2e
    # or: make e2e

These tests catch the class of bug that compile-time bundle checks miss —
e.g. a NameError when the bundle exec actually runs in Pyodide. See
issues/7.6 for the motivating incident.
"""

import pytest


# Maximum wait for Pyodide load + bundle eval + hydration. ~5s typical on a
# warm cache, more on first run. Generous to absorb CI variance.
HYDRATION_TIMEOUT_MS = 45_000


def _collect_browser_errors(page):
    """Attach listeners that record any console.error / pageerror events.

    Returns a list that the test reads after navigation. We capture both:
    - `console.error` (where Pyodide's PythonError lands after exec failure),
    - `pageerror` (uncaught JS / promise rejections).
    """
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: (
            errors.append(f"[console.{msg.type}] {msg.text}")
            if msg.type == "error"
            else None
        ),
    )
    page.on("pageerror", lambda exc: errors.append(f"[pageerror] {exc}"))
    return errors


@pytest.mark.e2e
def test_03_interactive_loads_with_no_pyodide_errors(example_server, page):
    """The smoke test: example 03 boots, Pyodide loads, the bundle executes,
    hydration completes — and no console.error / pageerror fires along the way.

    This is the test that would have caught the `NameError: name 'store' is
    not defined` bug surfaced in the browser (issues/7.6) before it shipped.
    """
    base = example_server("03_interactive.py")
    errors = _collect_browser_errors(page)

    page.goto(base + "/")

    # Hydration is complete when the bootstrap script removes the "cloak"
    # <style> element (see app.py:_inject_client_side). If the bundle exec
    # threw, this signal never arrives and we time out.
    page.wait_for_function(
        "() => document.getElementById('violetear-cloak') === null",
        timeout=HYDRATION_TIMEOUT_MS,
    )

    # If anything blew up during init (top-level `await restore()` etc.),
    # PyodideError → console.error before the cloak fires. We assert silence.
    assert errors == [], "Browser errors after hydration:\n  " + "\n  ".join(errors)

    # Cheap sanity check that the SSR-rendered values are present after
    # hydration. The meters input was server-rendered with value="1.0".
    meters_value = page.input_value('input[data-bind-value="UiState.meters"]')
    assert meters_value == "1.0"
