from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from settings import Kind

if TYPE_CHECKING:
    from pdf_line import PDFLine
    from pdf_page import PDFPage


@dataclass(eq=False)
class PDFParagraph:
    number: int
    kind: Kind = Kind.BODY
    lines: list[PDFLine] = field(default_factory=list)
    page: PDFPage | None = field(default=None, repr=False)

    def add_line(self, new_line: PDFLine) -> None:
        self.lines.append(new_line)
        new_line.paragraph = self

    @property
    def first_line(self) -> PDFLine:
        return self.lines[0]

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)

    @property
    def x0(self) -> float:
        return min(line.x0 for line in self.lines)

    @property
    def x1(self) -> float:
        return max(line.x1 for line in self.lines)

    @property
    def y0(self) -> float:
        return min(line.y0 for line in self.lines)

    @property
    def y1(self) -> float:
        return max(line.y1 for line in self.lines)

    def pitch(self) -> float | None:
        """Медианное расстояние между базовыми линиями соседних строк (None, если строка одна)."""
        if len(self.lines) < 2:
            return None
        return statistics.median(b.baseline - a.baseline for a, b in zip(self.lines, self.lines[1:]))

    @override
    def __str__(self) -> str:
        head = f"#{self.number} <{self.kind.value}>"
        return head + "".join(f"\n    {line}" for line in self.lines)
