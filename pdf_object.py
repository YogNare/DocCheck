from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)  # сравнение по идентичности: две строки с одинаковыми координатами - разные объекты
class PDFObject:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
