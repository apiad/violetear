import pytest
import runpy
from pathlib import Path


def get_example_params():
    results = []

    for css_file in (Path(__file__).parent.parent / "docs").rglob("*.css"):
        py_file = css_file.with_name(css_file.stem.replace("-", "_") + ".py")
        results.append((py_file, css_file))

    return results


@pytest.mark.parametrize("script,css", get_example_params())
def test_example(script, css):
    ns = runpy.run_path(script)

    assert "sheet" in ns

    sheet = ns["sheet"]
    result = sheet.render().split("\n")
    result.pop(2)

    with open(css) as fp:
        expected = fp.readlines()
        expected.pop(2)

    assert "\n".join(result) == "".join(expected)
