from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import override

import pymupdf

from pdf_image import PDFImage
from pdf_line import PDFLine
from pdf_object import PDFObject
from pdf_page import PDFPage
from pdf_paragraph import PDFParagraph
from settings import GostSettings, Kind
from units import mm_to_pt

_SENTENCE_END = (".", "!", "?", "…")
_ENUM_INTRO_END = (".", ";", ":", "!", "?")


def dominant_value(values: list[float], tol: float, min_count: int, min_share: float = 0.0) -> float | None:
    """Среднее значений из самого плотного окна шириной tol (или None, если плотного окна нет)."""
    if len(values) < min_count:
        return None
    values = sorted(values)
    best_count, best_lo, best_hi = 0, 0, 0
    lo = 0
    for hi, value in enumerate(values):
        while value - values[lo] > tol:
            lo += 1
        if hi - lo + 1 > best_count:
            best_count, best_lo, best_hi = hi - lo + 1, lo, hi
    if best_count < min_count or best_count / len(values) < min_share:
        return None
    window = values[best_lo:best_hi + 1]
    return sum(window) / len(window)


@dataclass
class _SplitContext:
    left: float
    right: float
    pitch: float | None   # обычный шаг между строками на странице
    justified: bool       # на странице есть общий правый край (выключка по ширине)


class PDFBook:
    """PDF, разобранный на страницы -> абзацы -> строки, плюс картинки."""

    def __init__(self, path: str, settings: GostSettings | None = None):
        self.path = path
        self.settings = settings or GostSettings()
        self._compile_patterns()
        self._paragraph_counter = 0

        self.pages: list[PDFPage] = self._read_pages(path)
        for page in self.pages:
            self._measure_edges(page)
            self._split_paragraphs(page)
            self._classify(page)

    @property
    def all_lines(self) -> list[PDFLine]:
        return [line for page in self.pages for line in page.lines]

    # ------------------------------------------------------------------ чтение PDF

    def _read_pages(self, path: str) -> list[PDFPage]:
        pages: list[PDFPage] = []
        with pymupdf.open(path) as doc:
            for index, src in enumerate(doc):
                page = PDFPage(index + 1, src.rect.width, src.rect.height)
                page.tables = self._find_tables(src)
                self._read_images(src, page)
                self._read_lines(src, page)
                pages.append(page)
        return pages

    def _find_tables(self, src: pymupdf.Page) -> list[PDFObject]:
        if not self.settings.ignore_tables:
            return []
        try:
            return [PDFObject(*table.bbox) for table in src.find_tables().tables]
        except Exception:  # старая версия PyMuPDF или сбой поиска - просто не выделяем таблицы
            return []

    @staticmethod
    def _inside(obj: PDFObject, areas: list[PDFObject]) -> bool:
        cx, cy = obj.center_x, (obj.y0 + obj.y1) / 2
        return any(a.x0 <= cx <= a.x1 and a.y0 <= cy <= a.y1 for a in areas)

    def _read_images(self, src: pymupdf.Page, page: PDFPage) -> None:
        min_size = mm_to_pt(self.settings.figure.min_size_mm)
        for info in src.get_image_info():
            image = PDFImage(*info["bbox"])
            if image.width < min_size or image.height < min_size:
                continue  # значки, формулы-картинки
            if self._inside(image, page.tables):
                continue
            page.add_image(image)

    def _read_lines(self, src: pymupdf.Page, page: PDFPage) -> None:
        ps = self.settings.page
        zone = mm_to_pt(ps.margin_zone_tolerance_mm)
        top_limit = mm_to_pt(ps.margin_top_mm) + zone
        bottom_limit = page.height - mm_to_pt(ps.margin_bottom_mm) - zone

        raw_lines: list[PDFLine] = []
        # rawdict нужен, чтобы брать границы строки по первому/последнему НЕпробельному символу:
        # пробел в конце строки входит в рамку строки и сдвигает поле и центр на ~1 мм
        for block in src.get_text("rawdict", flags=pymupdf.TEXTFLAGS_TEXT)["blocks"]:
            if block["type"] != 0:
                continue
            for raw in block["lines"]:
                if abs(raw["dir"][1]) > 0.1:  # вертикальный текст пропускаем
                    continue
                spans = [(sp, "".join(ch["c"] for ch in sp["chars"])) for sp in raw["spans"]]
                spans = [(sp, text) for sp, text in spans if text.strip()]
                if not spans:
                    continue
                main = max(spans, key=lambda item: len(item[1].strip()))[0]  # преобладающий шрифт строки
                glyphs = [ch for sp, _ in spans for ch in sp["chars"] if not ch["c"].isspace()]
                raw_lines.append(PDFLine(
                    min(ch["bbox"][0] for ch in glyphs), raw["bbox"][1],
                    max(ch["bbox"][2] for ch in glyphs), raw["bbox"][3],
                    text="".join(text for _, text in spans).strip(),
                    font=main["font"],
                    font_size=main["size"],
                    bold=bool(main["flags"] & 16) or "bold" in main["font"].lower(),
                    baseline=main["origin"][1],
                ))

        for line in self._merge_same_baseline(raw_lines):
            if self._inside(line, page.tables):
                continue
            if line.y1 <= top_limit:
                line.page = page
                page.header_lines.append(line)
            elif line.y0 >= bottom_limit:
                line.page = page
                page.footer_lines.append(line)
            else:
                page.add_line(line)

    @staticmethod
    def _merge_same_baseline(lines: list[PDFLine]) -> list[PDFLine]:
        """Куски текста на одной строке (например, номер + табуляция + название) склеиваем в одну строку."""
        lines = sorted(lines, key=lambda ln: ln.baseline)
        groups: list[list[PDFLine]] = []
        for line in lines:
            if groups and abs(line.baseline - groups[-1][0].baseline) < 0.25 * line.font_size:
                groups[-1].append(line)
            else:
                groups.append([line])

        merged: list[PDFLine] = []
        for group in groups:
            group.sort(key=lambda ln: ln.x0)
            current = group[0]
            for nxt in group[1:]:
                if nxt.x0 - current.x1 > 4 * current.font_size:  # далеко - это другая колонка, не склеиваем
                    merged.append(current)
                    current = nxt
                    continue
                main = current if len(current.text) >= len(nxt.text) else nxt
                current = PDFLine(
                    min(current.x0, nxt.x0), min(current.y0, nxt.y0),
                    max(current.x1, nxt.x1), max(current.y1, nxt.y1),
                    text=f"{current.text} {nxt.text}", font=main.font, font_size=main.font_size,
                    bold=main.bold, baseline=main.baseline,
                )
            merged.append(current)
        return merged

    # ------------------------------------------------------------------ края текста

    def _measure_edges(self, page: PDFPage) -> None:
        """Левый край текста и край выключки вправо по самому частому положению строк."""
        if len(page.lines) < 3:
            return
        tol = mm_to_pt(self.settings.tolerances.position_mm)
        page.left_edge = dominant_value([ln.x0 for ln in page.lines], tol, min_count=3, min_share=0.25)
        page.right_edge = dominant_value([ln.x1 for ln in page.lines], tol, min_count=3, min_share=0.3)

    # ------------------------------------------------------------------ абзацы

    def _split_paragraphs(self, page: PDFPage) -> None:
        if not page.lines:
            return
        page.lines.sort(key=lambda ln: (ln.baseline, ln.x0))
        left = page.left_edge if page.left_edge is not None else mm_to_pt(self.settings.page.margin_left_mm)
        right = page.right_edge if page.right_edge is not None else max(ln.x1 for ln in page.lines)

        ctx = _SplitContext(left, right, self._typical_pitch(page), justified=page.right_edge is not None)

        current: PDFParagraph | None = None
        for line in page.lines:
            if current is None or self._starts_new_paragraph(current, line, ctx):
                self._paragraph_counter += 1
                current = PDFParagraph(self._paragraph_counter, page=page)
                page.paragraphs.append(current)
            current.add_line(line)

    @staticmethod
    def _typical_pitch(page: PDFPage) -> float | None:
        """Обычный шаг между строками внутри абзаца на странице (медиана)."""
        steps = [b.baseline - a.baseline for a, b in zip(page.lines, page.lines[1:])
                 if 0 < b.baseline - a.baseline < 3 * a.font_size and abs(a.font_size - b.font_size) < 0.5]
        return statistics.median(steps) if len(steps) >= 3 else None

    def _starts_new_paragraph(self, par: PDFParagraph, line: PDFLine, ctx: _SplitContext) -> bool:
        h = self.settings.heuristics
        left, right = ctx.left, ctx.right
        prev = par.lines[-1]

        # 1. сменилось начертание или кегль (заголовок -> текст)
        if prev.bold != line.bold or abs(prev.font_size - line.font_size) > 0.5:
            return True

        # 2. вертикальный разрыв больше обычного шага между строками
        pitch = par.pitch() or ctx.pitch
        limit = 1.4 * pitch if pitch else h.gap_factor * line.font_size
        if line.baseline - prev.baseline > limit:
            return True

        # 3. строка начинается как заголовок или подпись
        if self._starts_element(line.text):
            return True

        # 4. центрированная строка продолжает центрированную подпись/заголовок (структурные заголовки однострочные)
        if (self._may_wrap_centered(par.first_line.text)
                and self._centered_like(prev, left, right) and self._centered_like(line, left, right)):
            return False

        # 5. красная строка
        if line.x0 - left > mm_to_pt(h.indent_detect_mm):
            return True

        # 6. предыдущая строка короткая и закончилась точкой: значит, это был конец абзаца
        prev_text = prev.text.rstrip()
        if ctx.justified and prev_text.endswith(_SENTENCE_END) and right - prev.x1 > mm_to_pt(h.short_line_mm):
            return True

        # 7. маркер перечисления после законченного предложения или двоеточия
        if self._rx_list.match(line.text) and prev_text.endswith(_ENUM_INTRO_END):
            return True

        return False

    def _may_wrap_centered(self, first_line_text: str) -> bool:
        return any(rx.match(first_line_text) for rx in (
            self._rx_figure, self._rx_figure_prefix, self._rx_table, self._rx_h1, self._rx_h2, self._rx_h3,
        ))

    def _centered_like(self, line: PDFLine, left: float, right: float) -> bool:
        margin = mm_to_pt(self.settings.heuristics.indent_detect_mm)
        tol = 3 * mm_to_pt(self.settings.tolerances.position_mm)
        return (line.x0 - left > margin and right - line.x1 > margin
                and abs(line.center_x - (left + right) / 2) <= tol)

    # ------------------------------------------------------------------ тип абзаца

    def _compile_patterns(self) -> None:
        p = self.settings.patterns
        self._rx_structural = re.compile(p.structural, re.IGNORECASE)
        self._rx_h1 = re.compile(p.heading_1)
        self._rx_h2 = re.compile(p.heading_2)
        self._rx_h3 = re.compile(p.heading_3)
        self._rx_list = re.compile(p.list_item)
        self._rx_figure = re.compile(p.figure_caption)
        self._rx_figure_prefix = re.compile(p.figure_caption_prefix)
        self._rx_table = re.compile(p.table_caption)

    def _starts_element(self, text: str) -> bool:
        return any(rx.match(text) for rx in (
            self._rx_structural, self._rx_h3, self._rx_h2, self._rx_h1, self._rx_figure, self._rx_table,
        ))

    def _classify(self, page: PDFPage) -> None:
        for par in page.paragraphs:
            par.kind = self._kind_of(par, page)

    def _kind_of(self, par: PDFParagraph, page: PDFPage) -> Kind:
        first = par.first_line.text
        if self._rx_structural.match(first):
            return Kind.HEADING_STRUCT
        if self._rx_table.match(first):
            return Kind.TABLE_CAPTION
        if self._rx_figure.match(first) or (self._rx_figure_prefix.match(first) and self._is_under_image(par, page)):
            return Kind.FIGURE_CAPTION
        if len(par.lines) <= 3:  # заголовок не бывает длинным
            for rx, kind in ((self._rx_h3, Kind.HEADING_3), (self._rx_h2, Kind.HEADING_2), (self._rx_h1, Kind.HEADING_1)):
                if rx.match(first):
                    return kind
        if self._rx_list.match(first):
            return Kind.LIST_ITEM
        return Kind.BODY

    def _is_under_image(self, par: PDFParagraph, page: PDFPage) -> bool:
        max_gap = mm_to_pt(self.settings.figure.caption_max_gap_mm)
        return any(0 <= par.y0 - image.y1 <= max_gap for image in page.images)

    # ------------------------------------------------------------------ вывод

    @override
    def __str__(self) -> str:
        return "".join(f"--------\n{page}" for page in self.pages)
