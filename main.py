import pymupdf
import pdf_book

def load_pages(source: str) -> pdf_book.PDFBook:
    new_book = pdf_book.PDFBook()

def main():
    doc = pymupdf.open("samples/FishText.pdf")
    book: list[pdf_page.PDFPage] = []
    num: int = 0
    for page in doc:
        book.append(pdf_page.PDFPage(len(book)))
        for line in page.get_text_blocks():
            book[-1].add_line(pdf_line.PDFLine(line))

        num += 1


    for page in book:
        print(page)

if __name__ == "__main__":
    main()