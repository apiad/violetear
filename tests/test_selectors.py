import pytest
from violetear.selector import Selector


@pytest.mark.parametrize("tag", ["div", "p", "body", "something-funny"])
def test_tag_selector(tag):
    assert Selector.parse(tag).css() == tag
