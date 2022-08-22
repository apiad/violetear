from __future__ import annotations
from typing import Literal, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from violetear.units import Unit, repeat, minmax

    GridTemplate = Union[Unit, repeat, minmax]
    GridSize = Union[Unit, minmax]

else:
    GridTemplate = None
    GridSize = None

FontWeight = Union[int, Literal["lighter", "normal", "bold", "bolder"]]
