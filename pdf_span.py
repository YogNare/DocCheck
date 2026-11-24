from dataclasses import dataclass


@dataclass
class PDFSpan:
    text: str
    font: str
    size: int
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def origin(self):
        return (self.x0/2 + self.x1/2), (self.y0/2 + self.y1/2)

    def __str__(self) -> str:
        return f" [{self.text}] "
