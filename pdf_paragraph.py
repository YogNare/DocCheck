from dataclasses import field
from os import linesep

import pdf_line

class PDFParagraph():
    lines: list[pdf_line.PDFLine] = field(default_factory=list)
    number: int

    def __init__(self, num: int):
        self.number = num
        return

    def add_line(self, new_line: pdf_line.PDFLine) -> None:
        self.lines.append(new_line)
        return

    def get_number(self) -> int:
        return self.number

    def get_lines(self) -> list[pdf_line.PDFLine]:
        return self.lines