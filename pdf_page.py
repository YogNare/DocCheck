from dataclasses import field, dataclass

import pdf_line

@dataclass(eq=False)
class PDFPage():

    number: int
    width: int
    height: int

    header: pdf_line.PDFLine | None = None
    footer: pdf_line.PDFLine | None = None

    lines: list[pdf_line.PDFLine] = field(default_factory=list)

    def add_line(self, new_line: pdf_line.PDFLine) -> None:
        self.lines.append(new_line)
        new_line.page = self
        return

    def __str__(self) -> str:
        return f'{str(self.header)}\n-\n' + "".join(f"{str(line)}\n" for line in self.lines) + f'-\n{self.footer}\n'