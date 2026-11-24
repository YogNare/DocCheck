from dataclasses import dataclass, field
from typing import override

import pdf_line
import pdf_page
import pdf_paragraph

# fixme: временная заглушка
k = 0.35

@dataclass
class PDFBook:

    lines: list[pdf_line.PDFLine] = field(default_factory=list)

    def __init__(self, path: str):
        self.pages: list[pdf_page.PDFPage] = []
        self.lines = list()
        self._read_pages(path)

    def _read_pages(self, path: str) -> None:
        import pymupdf
        doc = pymupdf.open(path)
        lines_start: int = 0
        for page in doc:
            prev = {"origin": 0, "size": 0}
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # todo: проверить валидность формулы
                            if abs(span["origin"][1] - prev["origin"]) < k * max(span["size"], prev["size"]):
                                self.lines[-1].add_span(span)
                            else:
                                new_line: pdf_line.PDFLine = pdf_line.PDFLine()
                                new_line.add_span(span)
                                if not (len(new_line.spans) > 0):
                                    continue
                                self.lines.append(new_line)

                            prev["origin"] = span["origin"][1]
                            prev["size"] = span["size"]


            self.pages.append(
                pdf_page.PDFPage(
                    len(self.pages) + 4,
                    page.mediabox_size[0],
                    page.mediabox_size[1],
                    self.lines,
                    range(lines_start, len(self.lines))
                )
            )
            lines_start = len(self.lines)

        return

    def _split_paragraphs(self) -> None:
        paragraphs = []
        space: float = self.standard_space
        prev_line: "pdf_line.PDFLine | None" = None
        # for line in self.get_all_lines:
        #     if line.x0 > first_space and (prev_line == None or prev_line.text[-1] in [".", "...", ""])

    @property
    def standard_space(self) -> float:
        count = 0
        res = 0
        for i in self.lines:
            res += i.x0
            count += 1

        return res/count

    @override
    def __str__(self) -> str:
        return "".join(f"{page}\n" for page in self.pages)