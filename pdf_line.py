from dataclasses import dataclass, field
from typing import override

import pdf_object
import pdf_page
import pdf_paragraph


@dataclass(eq=False)
class PDFLine(pdf_object.PDFObject):
    text: str
    font: str
    font_size: int

    page:  "pdf_page.PDFPage | None" = field(repr=False)

    position:  "pdf_paragraph.PDFParagraph | None" = field(default=None, repr=False)

    @staticmethod
    def _clean(text: str) -> str:
        return text.replace("\n", "")

    @override
    def __str__(self) -> str:
        return f"({self.x0:.2f}, {self.y0:.2f}), ({self.x1:.2f}, {self.y1:.2f}) | {self.text} - font={self.font}, font_size={self.font_size}"
