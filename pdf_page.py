from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from pdf_object import PDFObject
from units import pt_to_mm

if TYPE_CHECKING:
    from pdf_image import PDFImage
    from pdf_line import PDFLine
    from pdf_paragraph import PDFParagraph


@dataclass(eq=False)
class PDFPage:
    number: int  # номер листа, начиная с 1
    width: float  # pt
    height: float  # pt

    lines: list[PDFLine] = field(default_factory=list)          # строки основного текста
    header_lines: list[PDFLine] = field(default_factory=list)   # строки в верхнем поле
    footer_lines: list[PDFLine] = field(default_factory=list)   # строки в нижнем поле
    images: list[PDFImage] = field(default_factory=list)
    tables: list[PDFObject] = field(default_factory=list)       # области таблиц (их текст не проверяем)
    paragraphs: list[PDFParagraph] = field(default_factory=list)

    # измеренные по тексту края (None, если данных мало): левый край и край выключки вправо
    left_edge: float | None = None
    right_edge: float | None = None

    def add_line(self, new_line: PDFLine) -> None:
        self.lines.append(new_line)
        new_line.page = self

    def add_image(self, image: PDFImage) -> None:
        self.images.append(image)
        image.page = self

    @override
    def __str__(self) -> str:
        out = [f"=== Страница {self.number}: {pt_to_mm(self.width):.0f} x {pt_to_mm(self.height):.0f} мм ==="]
        out += [f"[верхнее поле] {line}" for line in self.header_lines]
        out += [str(image) for image in self.images]
        out += [str(par) for par in self.paragraphs]
        out += [f"[нижнее поле] {line}" for line in self.footer_lines]
        return "\n".join(out) + "\n"
