import pytest
from violetear.selector import Selector


@pytest.mark.parametrize("selector", ["div", "p", "body", "something-funny"])
def test_selector(selector):
    assert Selector.parse(selector).css() == selector
