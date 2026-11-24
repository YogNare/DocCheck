import pdf_book

class PDFBookParser:
    book: pdf_book.PDFBook | None= None

    def __init__(self, book: pdf_book.PDFBook):
        self.book = book

    def paragraph_split(self):
