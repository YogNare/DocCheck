from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from pdf_object import PDFObject
from units import pt_to_mm

if TYPE_CHECKING:
    from pdf_page import PDFPage


@dataclass(eq=False)
class PDFImage(PDFObject):
    page: PDFPage | None = field(default=None, repr=False)

    @override
    def __str__(self) -> str:
        return (f"[РИСУНОК] ({pt_to_mm(self.x0):.1f}, {pt_to_mm(self.y0):.1f}) - "
                f"({pt_to_mm(self.x1):.1f}, {pt_to_mm(self.y1):.1f}) мм, "
                f"{pt_to_mm(self.width):.1f} x {pt_to_mm(self.height):.1f} мм")
