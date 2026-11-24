from dataclasses import dataclass, field

import parameters
import pdf_line


@dataclass(eq=False)
class PDFPage:
    number: int
    width: int
    height: int

    all_lines: list[pdf_line.PDFLine] = field(repr=False)
    lines: range

    header: range = field(init=False)
    body: range = field(init=False)
    footer: range = field(init=False)

    def __post_init__(self) -> None:
        self._split_header_footer()

    def _split_header_footer(self) -> None:
        params = parameters.Parameters
        # fixme: настроить параметр лучше
        tolerance = 2

        body_start = self.lines.start
        body_stop = self.lines.stop

        # todo: обновить проверку на верхний колонтитул
        for i in self.lines:
            if abs(self.all_lines[i].origin - params.header_origin) > tolerance:
                break
            body_start = i + 1

        for i in reversed(range(body_start, body_stop)):
            if abs(self.all_lines[i].origin - params.footer_origin) > tolerance:
                break
            body_stop = i

        self.header = range(self.lines.start, body_start)
        self.body = range(body_start, body_stop)
        self.footer = range(body_stop, self.lines.stop)

    def __str__(self) -> str:
        return (f"===страница {self.number}===\n"
                f"[body]:\n"
                f"{"".join(f"\t{self.all_lines[i]}\n" for i in self.body)}\n"
                f"[footer]:\n"
                f"{"".join(f"\t{self.all_lines[i]}\n" for i in self.footer)}")