import argparse
from pathlib import Path

from checker import GostChecker, format_report
from pdf_book import PDFBook
from settings import GostSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверка оформления PDF по ГОСТ")
    parser.add_argument("pdf", nargs="?", default="samples/PDFExample 1.pdf", help="путь к PDF")
    parser.add_argument("-o", "--out", default="samples/report.txt", help="куда сохранить отчёт")
    parser.add_argument("--dump", default=None, help="сохранить разбор документа (страницы/абзацы/строки) для отладки")
    parser.add_argument("--full", action="store_true", help="не сворачивать одинаковые замечания")
    args = parser.parse_args()

    settings = GostSettings()  # все настройки оформления: settings.py
    book = PDFBook(args.pdf, settings)

    if args.dump:
        Path(args.dump).write_text(str(book), encoding="utf-8")

    report = format_report(GostChecker(book).check(), group=not args.full)
    Path(args.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
