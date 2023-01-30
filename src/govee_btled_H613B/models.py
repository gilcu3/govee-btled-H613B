from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoveeState:

    power: bool = False
    rgb: tuple[int, int, int] = (0, 0, 0)
    w_index: int = 0
    brightness: int = 0
