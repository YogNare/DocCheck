from dataclasses import dataclass, field

import pdf_line
import pdf_page
import pdf_paragraph


@dataclass
class PDFBook():
    lines: list[pdf_line.PDFLine] = field(default_factory=list)
    pages: list[pdf_page.PDFPage] = field(default_factory=list)
    paragraphs: list[pdf_paragraph.PDFParagraph] = field(default_factory=list)