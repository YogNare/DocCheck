from base64 import encode

import pdf_book


def main():
    book = pdf_book.PDFBook("samples/PDFExample 1.pdf")
    with open("samples/out", "w", encoding="utf-8") as output:
        output.write(f'{book}')

if __name__ == "__main__":
    main()