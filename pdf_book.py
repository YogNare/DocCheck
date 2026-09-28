from dataclasses import dataclass, field
from typing import override

import pdf_line
import pdf_page
import pdf_paragraph


@dataclass
class PDFBook:

    # read_line =

    def __init__(self, path: str):
        self.pages = self._read_pages(path)

    @property
    def get_all_lines(self) -> list["pdf_line.PDFLine"]:
        return [l for p in self.pages for l in p.lines]

    @staticmethod
    def _read_pages(path: str) -> list["pdf_page.PDFPage"]:
        import pymupdf
        doc = pymupdf.open(path)
        pages = []
        for page in doc:
            new_page = pdf_page.PDFPage(len(pages), page.mediabox_size[0], page.mediabox_size[1])
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:
                    for line in block["lines"]:
                        font: str = line["spans"][0]['font']
                        font_size: int = line["spans"][0]['size']
                        x0: float = line["spans"][0]['bbox'][0]
                        y0: float = line["spans"][0]['bbox'][1]
                        x1: float = line["spans"][-1]['bbox'][2]
                        y1: float = line["spans"][-1]['bbox'][3]
                        text: str = ""
                        for span in line["spans"]:
                            if font != span['font']:
                                pass
                            if font_size != span['size']:
                                pass
                            text += span['text']
                        line = pdf_line.PDFLine(x0, y0, x1, y1, text, font, font_size, new_page)
                        if y0 < 40:
                            new_page.header = line
                        elif y0 > 780:
                            new_page.footer = line
                        else:
                            new_page.add_line(line)

            pages.append(new_page)

        return pages

    def _split_paragraphs(self) -> None:
        paragraphs = []
        # for line in self.get_all_lines:
        #     if

        pass

    @override
    def __str__(self) -> str:
        return "".join(f"--------\n{str(page)}" for page in self.pages)