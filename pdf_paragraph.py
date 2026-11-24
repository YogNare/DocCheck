from dataclasses import field, dataclass
from os import linesep

import pdf_line

@dataclass
class PDFParagraph:
    number: int
    lines: list[pdf_line.PDFLine] = field(default_factory=list)

    def add_line(self, new_line: pdf_line.PDFLine) -> None:
        self.lines.append(new_line)
        return

    def get_number(self) -> int:
        return self.number

    def get_lines(self) -> list[pdf_line.PDFLine]:
        return self.lines