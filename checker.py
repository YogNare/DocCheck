from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

from pdf_book import PDFBook
from pdf_image import PDFImage
from pdf_object import PDFObject
from pdf_page import PDFPage
from pdf_paragraph import PDFParagraph
from settings import ALIGNMENT_RU, KIND_RU, Alignment, ElementStyle, GostSettings, Kind
from units import mm_to_pt, pt_to_mm

_HEADINGS = (Kind.HEADING_STRUCT, Kind.HEADING_1, Kind.HEADING_2, Kind.HEADING_3)
_TEXT_KINDS = (Kind.BODY, Kind.LIST_ITEM)
_SENTENCE_END = (".", "!", "?", "…", ":", ";")
_ALIGNMENT_ORDER = (Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT, Alignment.JUSTIFY)

RULES_RU = {
    "page_size": "формат листа",
    "margin_left": "левое поле",
    "margin_right": "правое поле",
    "margin_overflow": "выход за поля",
    "page_number": "номер страницы",
    "margin_text": "текст в полях",
    "font": "шрифт",
    "font_size": "кегль",
    "bold": "полужирное начертание",
    "uppercase": "регистр",
    "trailing_dot": "точка в конце",
    "number_dot": "точка после номера",
    "alignment": "выравнивание",
    "left_indent": "отступ абзаца слева",
    "first_line_indent": "красная строка",
    "line_spacing": "междустрочный интервал",
    "caption_format": "формат подписи",
    "image_margins": "рисунок: поля",
    "image_alignment": "рисунок: выравнивание",
    "figure_caption": "рисунок: подпись",
}


@dataclass
class Violation:
    page: int
    rule: str
    message: str
    text: str = ""
    severity: str = "error"  # "error" | "warning"
    y: float = -1.0          # положение на странице (pt), для сортировки; -1 = относится к странице в целом

    def __str__(self) -> str:
        tail = f"  «{self.text}»" if self.text else ""
        return f"[{'ОШИБКА' if self.severity == 'error' else 'предупр.'}] {self.message}{tail}"


class GostChecker:
    def __init__(self, book: PDFBook, settings: GostSettings | None = None):
        self.book = book
        self.s = settings or book.settings
        self._tol = mm_to_pt(self.s.tolerances.position_mm)
        self._rx_figure_format = re.compile(self.s.patterns.figure_caption_format)
        self._rx_table_format = re.compile(self.s.patterns.table_caption_format)
        self._fonts = [self._norm(name) for name in self.s.font_names]

    # ------------------------------------------------------------------ общий обход

    def check(self) -> list[Violation]:
        result: list[Violation] = []
        pages = self.book.pages
        for index, page in enumerate(pages):
            skipped = page.number in self.s.skip_pages
            result += self._check_page_geometry(page, measure_margins=not skipped)
            result += self._check_page_number(page)
            if skipped:
                continue
            previous = pages[index - 1] if index else None
            for i, par in enumerate(page.paragraphs):
                continues = i == 0 and self._continues_previous_page(previous, par)
                result += self._check_paragraph(par, continues)
            for image in page.images:
                result += self._check_image(image)
        result.sort(key=lambda v: (v.page, v.y))
        return result

    # ------------------------------------------------------------------ вспомогательное

    def _area(self, page: PDFPage) -> tuple[float, float, float, float]:
        """Область текста по настройкам: left, top, right, bottom (pt)."""
        ps = self.s.page
        return (mm_to_pt(ps.margin_left_mm), mm_to_pt(ps.margin_top_mm),
                page.width - mm_to_pt(ps.margin_right_mm), page.height - mm_to_pt(ps.margin_bottom_mm))

    @staticmethod
    def _norm(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def _font_ok(self, font: str) -> bool:
        clean = self._norm(font.split("+")[-1])
        return any(allowed in clean for allowed in self._fonts)

    @staticmethod
    def _is_page_number(text: str) -> bool:
        return re.fullmatch(r"\d{1,4}\.?", text.strip()) is not None

    def _continues_previous_page(self, previous: PDFPage | None, par: PDFParagraph) -> bool:
        """Первый абзац страницы может быть продолжением абзаца с прошлой страницы (без красной строки)."""
        if par.first_line.text[:1].islower():
            return True
        if not previous or not previous.paragraphs:
            return False
        last = previous.paragraphs[-1]
        if last.kind not in _TEXT_KINDS:
            return False
        if not last.text.rstrip().endswith(_SENTENCE_END):
            return True
        # Предложение кончилось ровно на границе листов. Если последняя строка дотянулась до правого края
        # (или края нет, текст без выключки), считаем, что абзац продолжается: красную строку не требуем.
        edge = previous.right_edge
        return edge is None or last.lines[-1].x1 >= edge - self._tol

    def _center_x(self, page: PDFPage) -> float:
        """Центр области текста. Если по тексту измерены оба края, берём фактический центр: неверные поля
        уже отмечены отдельным замечанием, и лишний раз «не по центру» для каждого элемента не нужно."""
        if page.left_edge is not None and page.right_edge is not None:
            return (page.left_edge + page.right_edge) / 2
        left, _, right, _ = self._area(page)
        return (left + right) / 2

    def _box_aligned(self, obj: PDFObject, alignment: Alignment, page: PDFPage) -> bool:
        left, _, right, _ = self._area(page)
        match alignment:
            case Alignment.CENTER:
                return abs(obj.center_x - self._center_x(page)) <= self._tol
            case Alignment.RIGHT:
                return abs(obj.x1 - right) <= self._tol
            case Alignment.LEFT:
                return abs(obj.x0 - left) <= self._tol
            case _:
                return True

    # ------------------------------------------------------------------ страница

    def _check_page_geometry(self, page: PDFPage, measure_margins: bool) -> list[Violation]:
        ps, tol = self.s.page, self._tol
        out: list[Violation] = []

        w, h = pt_to_mm(page.width), pt_to_mm(page.height)
        expected = sorted((ps.width_mm, ps.height_mm))
        if any(abs(a - e) > ps.size_tolerance_mm for a, e in zip(sorted((w, h)), expected)):
            out.append(Violation(page.number, "page_size",
                                 f"Формат листа {w:.0f} x {h:.0f} мм, требуется {ps.width_mm:.0f} x {ps.height_mm:.0f} мм"))

        left, top, right, bottom = self._area(page)
        measured_sides: set[str] = set()
        if measure_margins:
            if page.left_edge is not None and abs(page.left_edge - left) > tol:
                measured_sides.add("левое")
                out.append(Violation(page.number, "margin_left",
                                     f"Левое поле около {pt_to_mm(page.left_edge):.1f} мм, требуется {ps.margin_left_mm:g} мм"))
            if page.right_edge is not None:
                actual = page.width - page.right_edge
                if abs(actual - mm_to_pt(ps.margin_right_mm)) > tol:
                    measured_sides.add("правое")
                    out.append(Violation(page.number, "margin_right",
                                         f"Правое поле около {pt_to_mm(actual):.1f} мм, требуется {ps.margin_right_mm:g} мм"))

        objects = [*page.lines, *page.images]
        if objects:
            overflow = {
                "левое": left - min(o.x0 for o in objects),
                "правое": max(o.x1 for o in objects) - right,
                "верхнее": top - min(o.y0 for o in objects),
                "нижнее": max(o.y1 for o in objects) - bottom,
            }
            for side, value in overflow.items():
                if value > tol and side not in measured_sides:
                    out.append(Violation(page.number, "margin_overflow",
                                         f"Текст или рисунок заходит в {side} поле на {pt_to_mm(value):.1f} мм"))
        return out

    def _check_page_number(self, page: PDFPage) -> list[Violation]:
        pn = self.s.page_number
        if not pn.required or (page.number == 1 and pn.skip_first_page):
            return []
        bottom = pn.position == "bottom"
        where = "внизу" if bottom else "вверху"
        zone = page.footer_lines if bottom else page.header_lines
        other = page.header_lines if bottom else page.footer_lines
        out: list[Violation] = []

        numbers = [ln for ln in zone if self._is_page_number(ln.text)]
        if not numbers:
            if any(self._is_page_number(ln.text) for ln in other):
                out.append(Violation(page.number, "page_number", f"Номер страницы стоит не там: требуется {where} листа"))
            else:
                out.append(Violation(page.number, "page_number", f"Не найден номер страницы (ожидается {where} листа)"))
        else:
            line = numbers[0]
            text = line.text.strip()
            if text.endswith("."):
                out.append(Violation(page.number, "page_number", "После номера страницы точка не ставится", text))
            expected = page.number + pn.number_offset
            if int(text.rstrip(".")) != expected:
                out.append(Violation(page.number, "page_number",
                                     f"Номер страницы {text.rstrip('.')}, ожидается {expected} (нумерация сквозная)"))
            if not self._box_aligned(line, pn.alignment, page):
                out.append(Violation(page.number, "page_number",
                                     f"Номер страницы должен стоять {ALIGNMENT_RU[pn.alignment]}", text))

        if pn.warn_other_text_in_margins:
            for line in [*page.header_lines, *page.footer_lines]:
                if not self._is_page_number(line.text):
                    out.append(Violation(page.number, "margin_text", "В поле страницы есть текст, не являющийся номером",
                                         line.text[:60], severity="warning", y=line.y0))
        return out

    # ------------------------------------------------------------------ абзацы

    def _alignment_options(self, par: PDFParagraph) -> set[Alignment]:
        """Какие выравнивания геометрически возможны для абзаца (может быть несколько: строка на всю ширину и т.п.)."""
        page, lines, tol = par.page, par.lines, self._tol
        left, _, right, _ = self._area(page)
        options: set[Alignment] = set()

        if all(abs(ln.center_x - self._center_x(page)) <= tol for ln in lines):
            options.add(Alignment.CENTER)

        right_ref = page.right_edge if page.right_edge is not None else right
        if all(abs(ln.x1 - right_ref) <= tol for ln in lines):
            options.add(Alignment.RIGHT)

        base = page.left_edge if page.left_edge is not None else left
        if len(lines) == 1:
            # последняя (она же единственная) строка при выключке по ширине выглядит как выровненная влево
            offset = lines[0].x0 - base
            if -tol <= offset <= mm_to_pt(self.s.tolerances.max_left_indent_mm):
                options |= {Alignment.LEFT, Alignment.JUSTIFY}
        else:
            starts = [ln.x0 for ln in lines[1:]]  # первую строку не берём: у неё красная строка
            if max(starts) - min(starts) <= tol:
                options.add(Alignment.LEFT)
                if all(abs(ln.x1 - right_ref) <= tol for ln in lines[:-1]):
                    options.add(Alignment.JUSTIFY)
        return options

    def _check_paragraph(self, par: PDFParagraph, continues: bool) -> list[Violation]:
        style: ElementStyle | None = self.s.styles.get(par.kind)
        if style is None:
            return []
        page, tols = par.page, self.s.tolerances
        text = par.text
        snippet = text[:60] + ("…" if len(text) > 60 else "")
        label = KIND_RU[par.kind].capitalize()
        out: list[Violation] = []

        def add(rule: str, message: str) -> None:
            out.append(Violation(page.number, rule, f"{label}: {message}", snippet, y=par.y0))

        # --- шрифт, кегль, начертание, регистр, точка
        bad_fonts = sorted({ln.font.split("+")[-1] for ln in par.lines if not self._font_ok(ln.font)})
        if bad_fonts:
            add("font", f"шрифт {', '.join(bad_fonts)}, требуется {' / '.join(self.s.font_names)}")

        if style.font_size_pt is not None:
            bad = sorted({round(ln.font_size, 1) for ln in par.lines
                          if abs(ln.font_size - style.font_size_pt) > tols.font_size_pt})
            if bad:
                add("font_size", f"кегль {', '.join(f'{v:g}' for v in bad)} pt, требуется {style.font_size_pt:g} pt")

        if style.bold is not None:
            wrong = sum(ln.bold != style.bold for ln in par.lines)
            if wrong * 2 >= len(par.lines):
                add("bold", "должен быть полужирным" if style.bold else "не должен быть полужирным")

        letters = [c for c in text if c.isalpha()]
        if style.uppercase is not None and letters:
            all_upper = all(c.isupper() for c in letters)
            if style.uppercase and not all_upper:
                add("uppercase", "должен быть набран ПРОПИСНЫМИ буквами")
            elif style.uppercase is False and all_upper and len(letters) > 3:
                add("uppercase", "не должен быть набран целиком прописными")

        if style.no_trailing_dot and text.rstrip().endswith("."):
            add("trailing_dot", "в конце точка не ставится")
        if par.kind in _HEADINGS and re.match(r"^\d+(\.\d+)*\.\s", text):
            add("number_dot", "после номера точка не ставится")

        # --- выравнивание
        if style.alignment is not None:
            options = self._alignment_options(par)
            if style.alignment not in options:
                found = ", ".join(ALIGNMENT_RU[a] for a in _ALIGNMENT_ORDER if a in options) or "не удалось определить"
                add("alignment", f"выравнивание {found}; требуется {ALIGNMENT_RU[style.alignment]}")

        # --- отступы (для выровненных влево и по ширине)
        if style.alignment in (Alignment.LEFT, Alignment.JUSTIFY):
            base = page.left_edge if page.left_edge is not None else self._area(page)[0]
            rest = [ln.x0 for ln in par.lines[1:]]
            left_x = statistics.median(rest) if rest else None

            if left_x is not None and style.left_indent_mm is not None:
                actual = pt_to_mm(left_x - base)
                if abs(actual - style.left_indent_mm) > tols.position_mm:
                    add("left_indent", f"отступ всего абзаца слева {actual:.1f} мм, требуется {style.left_indent_mm:g} мм")

            skip_first_line = continues and par.kind in _TEXT_KINDS  # абзац перешёл с прошлой страницы
            if style.first_line_indent_mm is not None and not skip_first_line:
                ref = left_x if left_x is not None else base + mm_to_pt(style.left_indent_mm or 0)
                actual = pt_to_mm(par.first_line.x0 - ref)
                if abs(actual - style.first_line_indent_mm) > tols.position_mm:
                    add("first_line_indent", f"красная строка {actual:.1f} мм, требуется {style.first_line_indent_mm:g} мм")

        # --- междустрочный интервал
        if style.line_spacing is not None and len(par.lines) >= 2:
            size = statistics.median(ln.font_size for ln in par.lines)
            ratio = par.pitch() / (size * self.s.single_line_height_em)
            if abs(ratio - style.line_spacing) > tols.line_spacing:
                add("line_spacing", f"междустрочный интервал около {ratio:.2f}, требуется {style.line_spacing:g}")

        # --- формат подписей
        if par.kind is Kind.FIGURE_CAPTION and not self._rx_figure_format.match(text):
            add("caption_format", "подпись должна иметь вид «Рисунок N – Название» (тире «–» с пробелами)")
        if par.kind is Kind.TABLE_CAPTION and not self._rx_table_format.match(text):
            add("caption_format", "подпись должна иметь вид «Таблица N – Название» (тире «–» с пробелами)")
        return out

    # ------------------------------------------------------------------ рисунки

    def _find_caption(self, image: PDFImage) -> tuple[PDFParagraph, str] | None:
        gap = mm_to_pt(self.s.figure.caption_max_gap_mm)
        best: tuple[float, PDFParagraph, str] | None = None
        for par in image.page.paragraphs:
            if par.kind is not Kind.FIGURE_CAPTION:
                continue
            below, above = par.y0 - image.y1, image.y0 - par.y1
            if -self._tol <= below <= gap:
                candidate = (below, par, "below")
            elif -self._tol <= above <= gap:
                candidate = (above, par, "above")
            else:
                continue
            if best is None or candidate[0] < best[0]:
                best = candidate
        return (best[1], best[2]) if best else None

    def _check_image(self, image: PDFImage) -> list[Violation]:
        page, fig, tol = image.page, self.s.figure, self._tol
        left, _, right, _ = self._area(page)
        size = f"{pt_to_mm(image.width):.0f} x {pt_to_mm(image.height):.0f} мм"
        out: list[Violation] = []

        def add(rule: str, message: str) -> None:
            out.append(Violation(page.number, rule, f"Рисунок: {message}", size, y=image.y0))

        if image.x0 < left - tol or image.x1 > right + tol:
            add("image_margins", "выходит за границы области текста")

        if not self._box_aligned(image, fig.alignment, page):
            shift = pt_to_mm(image.center_x - self._center_x(page))
            hint = f" (сдвиг от центра {shift:+.1f} мм)" if fig.alignment is Alignment.CENTER else ""
            add("image_alignment", f"положение не соответствует требованию «{ALIGNMENT_RU[fig.alignment]}»{hint}")

        if fig.caption_required:
            found = self._find_caption(image)
            if found is None:
                add("figure_caption", "не найдена подпись вида «Рисунок N – Название» рядом с рисунком")
            elif found[1] != fig.caption_position:
                actual = "над" if found[1] == "above" else "под"
                needed = "над" if fig.caption_position == "above" else "под"
                add("figure_caption", f"подпись находится {actual} рисунком, требуется {needed} рисунком")
        return out


# ---------------------------------------------------------------------- отчёт

def format_report(violations: list[Violation], group: bool = True) -> str:
    """group=True: одинаковые замечания на странице сворачиваются в одну строку со счётчиком и примером."""
    if not violations:
        return "Нарушений не найдено.\n"

    by_page: dict[int, list[Violation]] = defaultdict(list)
    for v in violations:
        by_page[v.page].append(v)

    lines: list[str] = []
    for page in sorted(by_page):
        lines.append(f"Страница {page}")
        if not group:
            lines += [f"  {v}" for v in by_page[page]]
        else:
            grouped: dict[tuple[str, str, str], list[Violation]] = {}
            for v in by_page[page]:
                grouped.setdefault((v.rule, v.message, v.severity), []).append(v)
            for items in grouped.values():
                first = items[0]
                if len(items) == 1:
                    lines.append(f"  {first}")
                else:
                    tag = "ОШИБКА" if first.severity == "error" else "предупр."
                    lines.append(f"  [{tag}] {first.message}  (x{len(items)}, например: «{first.text}»)")
        lines.append("")

    errors = sum(v.severity == "error" for v in violations)
    lines.append(f"Итого: {len(violations)} (ошибок: {errors}, предупреждений: {len(violations) - errors})")
    lines.append("По правилам:")
    for rule, count in Counter(v.rule for v in violations).most_common():
        lines.append(f"  {RULES_RU.get(rule, rule)}: {count}")
    return "\n".join(lines) + "\n"
