from typing import override
import pdf_page
import pdf_paragraph


class PDFLine():
    x1: float
    y1: float
    x2: float
    y2: float

    position: pdf_paragraph.PDFParagraph
    page: pdf_page.PDFPage

    value: str

    font: str
    font_size: int

    def remove_enter(line: str) -> str:
        return line.replace("\n", "")

    def __init__(self, line: tuple):
        (self.x1, self.y1, self.x2, self.y2, self.value, self.position, self.page) = line
        self.value = PDFLine.remove_enter(self.value)
        return

    def add_to_line(self, upd_line: str) -> None:
        self.value += upd_line
        self.value = PDFLine.remove_enter(self.value)
        return

    def get_val(self) -> str:
        return self.value

    def set_font(self, font: str) -> None:
        self.font = font
        return

    def set_font_size(self, font_size: int) -> None:
        self.font_size = font_size
        return

    @override
    def __str__(self) -> str:
        return f"line: {self.position} - {self.x1} | {self.value} | {self.x2}"