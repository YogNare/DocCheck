from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from pdf_object import PDFObject
from units import pt_to_mm

if TYPE_CHECKING:  # только для аннотаций: так нет циклических импортов
    from pdf_page import PDFPage
    from pdf_paragraph import PDFParagraph


@dataclass(eq=False)
class PDFLine(PDFObject):
    text: str
    font: str
    font_size: float
    bold: bool
    baseline: float  # y базовой линии, по ней меряем междустрочный интервал

    page: PDFPage | None = field(default=None, repr=False)
    paragraph: PDFParagraph | None = field(default=None, repr=False)

    @override
    def __str__(self) -> str:
        return (f"({pt_to_mm(self.x0):.1f}, {pt_to_mm(self.y0):.1f}) - "
                f"({pt_to_mm(self.x1):.1f}, {pt_to_mm(self.y1):.1f}) мм | {self.text} "
                f"[{self.font}, {self.font_size:.1f} pt{', bold' if self.bold else ''}]")
