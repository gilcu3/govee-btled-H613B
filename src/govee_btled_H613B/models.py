from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoveeState:

    power: bool = False
    rgb: tuple[int, int, int] = (0, 0, 0)
    color_temp: int = 0
    brightness: int = 0
