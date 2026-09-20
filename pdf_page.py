from dataclasses import field, dataclass

import pdf_line

@dataclass
class PDFPage():

    number: int

    header: pdf_line.PDFLine | None = None
    footer: pdf_line.PDFLine | None = None

    lines: list[pdf_line.PDFLine] = field(default_factory=list)

    def add_line(self, new_line: pdf_line.PDFLine) -> None:
        self.lines.append(new_line)
        return

    def get_lines(self) -> list[pdf_line.PDFLine]:
        return self.lines

    def __str__(self) -> str:
        return "".join(f"{line.get_val()}\n" for line in self.lines)