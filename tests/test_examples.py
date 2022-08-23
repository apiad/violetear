import pytest
import runpy
from pathlib import Path


def get_example_params():
    results = []

    for py_file in (Path(__file__).parent.parent / "docs").rglob("*.py"):
        css_file = py_file.with_name(py_file.stem.replace("_", "-") + ".css")
        results.append((py_file, css_file))

    return results


@pytest.mark.parametrize("script,css", get_example_params())
def test_example(script, css):
    ns = runpy.run_path(script)

    assert "sheet" in ns

    sheet = ns["sheet"]
    result = sheet.render()

    with open(Path(__file__).parent / "expected_outputs" / css.name) as fp:
        expected = fp.read()

    assert result == expected
