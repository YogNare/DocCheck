from dataclasses import dataclass, field
from typing import override

import pdf_object
import pdf_page
import pdf_paragraph
import pdf_span


@dataclass(eq=False)
class PDFLine(pdf_object.PDFObject):

    spans: list[pdf_span.PDFSpan] = field(default_factory=list)
    page:  "pdf_page.PDFPage | None" = field(default=None, repr=False)
    paragraph:  "pdf_paragraph.PDFParagraph | None" = field(default=None, repr=False)

    def add_span(self, raw_span: dict) -> None:
        text = raw_span["text"].replace('\n', "")
        if text.strip():
            span: pdf_span.PDFSpan = pdf_span.PDFSpan(text, raw_span["font"], raw_span["size"], raw_span["origin"])
            self.spans.append(span)
            self.x0 = min(self.x0, raw_span["bbox"][0])
            self.y0 = min(self.y0, raw_span["bbox"][1])
            self.x1 = max(self.x1, raw_span["bbox"][2])
            self.y1 = max(self.y1, raw_span["bbox"][3])
        return

    @property
    def origin(self):
        return self.y0/2 + self.y1/2

    @override
    def __str__(self) -> str:
        return "".join(f"{span}" for span in self.spans)
