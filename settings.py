"""Все настройки проверки оформления собраны здесь.

Единицы: миллиметры (мм) и пункты (pt) для кегля.
Правило для стилей: None = этот параметр не проверяется.

Значения по умолчанию соответствуют типовым требованиям ГОСТ 7.32-2017 в редакции вузов
(Times New Roman 14, по ширине, интервал 1,5, красная строка 1,25 см, поля 30/15/20/20).
Если в вашей методичке иначе (например, правое поле 10 мм), меняйте здесь.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class Kind(str, Enum):
    """Типы элементов текста. Для каждого можно задать свой стиль (см. default_styles)."""
    BODY = "body"                        # обычный абзац
    HEADING_STRUCT = "heading_struct"    # ВВЕДЕНИЕ, ЗАКЛЮЧЕНИЕ, СОДЕРЖАНИЕ, СПИСОК ЛИТЕРАТУРЫ...
    HEADING_1 = "heading_1"              # 1 Название раздела
    HEADING_2 = "heading_2"              # 1.1 Название подраздела
    HEADING_3 = "heading_3"              # 1.1.1 Название пункта
    LIST_ITEM = "list_item"              # пункт перечисления
    FIGURE_CAPTION = "figure_caption"    # Рисунок 1 – Название
    TABLE_CAPTION = "table_caption"      # Таблица 1 – Название


ALIGNMENT_RU = {
    Alignment.LEFT: "по левому краю",
    Alignment.CENTER: "по центру",
    Alignment.RIGHT: "по правому краю",
    Alignment.JUSTIFY: "по ширине",
}

KIND_RU = {
    Kind.BODY: "абзац",
    Kind.HEADING_STRUCT: "структурный заголовок",
    Kind.HEADING_1: "заголовок раздела",
    Kind.HEADING_2: "заголовок подраздела",
    Kind.HEADING_3: "заголовок пункта",
    Kind.LIST_ITEM: "пункт перечисления",
    Kind.FIGURE_CAPTION: "подпись рисунка",
    Kind.TABLE_CAPTION: "подпись таблицы",
}


# --------------------------------------------------------------------------- страница

@dataclass
class PageSettings:
    width_mm: float = 210.0            # А4
    height_mm: float = 297.0
    margin_left_mm: float = 30.0       # отступ ВСЕГО текста от краёв листа (поля)
    margin_right_mm: float = 15.0
    margin_top_mm: float = 20.0
    margin_bottom_mm: float = 20.0
    size_tolerance_mm: float = 1.0
    # Строки, целиком лежащие в поле (± этот допуск), считаются колонтитулом/номером страницы.
    margin_zone_tolerance_mm: float = 2.0


@dataclass
class PageNumberSettings:
    required: bool = True
    position: str = "bottom"                  # "bottom" или "top"
    alignment: Alignment = Alignment.CENTER
    skip_first_page: bool = True              # на титульном листе номер не ставят (но лист считается)
    number_offset: int = 0                    # ожидаемый номер = порядковый номер листа + offset
    warn_other_text_in_margins: bool = True   # предупреждать о постороннем тексте в полях


# --------------------------------------------------------------------------- элементы

@dataclass
class ElementStyle:
    alignment: Alignment | None = None
    first_line_indent_mm: float | None = None   # отступ красной строки
    left_indent_mm: float | None = None         # отступ всего абзаца слева сверх поля (обычно 0)
    font_size_pt: float | None = None
    bold: bool | None = None
    uppercase: bool | None = None               # True: только ПРОПИСНЫЕ; False: не целиком прописные
    no_trailing_dot: bool = False               # запретить точку в конце
    line_spacing: float | None = None           # множитель: 1.0 / 1.5 / 2.0


def default_styles() -> dict[Kind, ElementStyle]:
    body = ElementStyle(
        alignment=Alignment.JUSTIFY, first_line_indent_mm=12.5, left_indent_mm=0.0,
        font_size_pt=14, bold=False, line_spacing=1.5,
    )
    return {
        Kind.BODY: body,
        Kind.LIST_ITEM: replace(body),
        # по центру, без красной строки, ПРОПИСНЫМИ, без точки
        Kind.HEADING_STRUCT: ElementStyle(
            alignment=Alignment.CENTER, first_line_indent_mm=0.0,
            font_size_pt=14, bold=True, uppercase=True, no_trailing_dot=True,
        ),
        # с абзацного отступа, слева, без точки
        Kind.HEADING_1: ElementStyle(
            alignment=Alignment.LEFT, first_line_indent_mm=12.5, left_indent_mm=0.0,
            font_size_pt=14, bold=True, no_trailing_dot=True,
        ),
        Kind.HEADING_2: ElementStyle(
            alignment=Alignment.LEFT, first_line_indent_mm=12.5, left_indent_mm=0.0,
            font_size_pt=14, bold=True, no_trailing_dot=True,
        ),
        Kind.HEADING_3: ElementStyle(
            alignment=Alignment.LEFT, first_line_indent_mm=12.5, left_indent_mm=0.0,
            font_size_pt=14, bold=True, no_trailing_dot=True,
        ),
        # подпись рисунка: по центру под рисунком, без точки в конце
        Kind.FIGURE_CAPTION: ElementStyle(
            alignment=Alignment.CENTER, first_line_indent_mm=0.0, bold=False, no_trailing_dot=True,
        ),
        # подпись таблицы: над таблицей, слева, без красной строки
        Kind.TABLE_CAPTION: ElementStyle(
            alignment=Alignment.LEFT, first_line_indent_mm=0.0, left_indent_mm=0.0,
            bold=False, no_trailing_dot=True,
        ),
    }


@dataclass
class FigureSettings:
    alignment: Alignment = Alignment.CENTER   # положение самой картинки на странице
    caption_required: bool = True
    caption_position: str = "below"           # "below" или "above"
    caption_max_gap_mm: float = 20.0          # макс. расстояние от картинки до подписи
    min_size_mm: float = 15.0                 # картинки меньше этого (формулы, значки) игнорируем


# --------------------------------------------------------------------------- распознавание

@dataclass
class Patterns:
    """Регулярные выражения для определения типа абзаца и формата подписей."""
    # проверяются без учёта регистра, чтобы поймать «Введение» вместо «ВВЕДЕНИЕ»
    structural: str = (
        r"^(РЕФЕРАТ|АННОТАЦИЯ|СОДЕРЖАНИЕ|ОГЛАВЛЕНИЕ|ВВЕДЕНИЕ|ЗАКЛЮЧЕНИЕ|"
        r"ТЕРМИНЫ И ОПРЕДЕЛЕНИЯ|ПЕРЕЧЕНЬ СОКРАЩЕНИЙ.*|ОБОЗНАЧЕНИЯ И СОКРАЩЕНИЯ|"
        r"СПИСОК\s+(ИСПОЛЬЗОВАННЫХ\s+)?(ИСТОЧНИКОВ|ЛИТЕРАТУРЫ)|БИБЛИОГРАФИЧЕСКИЙ СПИСОК|"
        r"ПРИЛОЖЕНИЕ\s+[А-ЯЁA-Z]\d?)\s*$"
    )
    heading_1: str = r"^\d+\s+[А-ЯЁA-Z]"
    heading_2: str = r"^\d+\.\d+\.?\s+[А-ЯЁA-Z]"
    heading_3: str = r"^\d+\.\d+\.\d+\.?\s+[А-ЯЁA-Z]"
    list_item: str = r"^([–—\-•]|[а-яё]\)|\d+\))\s+\S"
    # подпись по началу строки: «Рисунок 1 –», «Рис. 2.», «Рисунок 3» (одна на строке)
    figure_caption: str = r"^(Рисунок|Рис\.)\s*(\d+|[А-ЯA-Z]\.\d+)\s*([–—\-.:]|$)"
    figure_caption_prefix: str = r"^(Рисунок|Рис\.)\s*(\d+|[А-ЯA-Z]\.\d+)\b"
    table_caption: str = r"^Таблица\s*(\d+|[А-ЯA-Z]\.\d+)\s*([–—\-.:]|$)"
    # строгий формат подписи (тире именно «–»)
    figure_caption_format: str = r"^Рисунок\s+(\d+|[А-ЯA-Z]\.\d+)\s+–\s+\S"
    table_caption_format: str = r"^Таблица\s+(\d+|[А-ЯA-Z]\.\d+)(\s+–\s+\S.*)?$"


# --------------------------------------------------------------------------- допуски

@dataclass
class Tolerances:
    position_mm: float = 1.5          # допуск на отступы/выравнивание/поля
    font_size_pt: float = 0.3
    line_spacing: float = 0.1
    max_left_indent_mm: float = 25.0  # однострочный абзац с отступом до этого значения считается «слева»


@dataclass
class Heuristics:
    """Параметры разбиения строк на абзацы. Обычно трогать не нужно."""
    indent_detect_mm: float = 3.0      # строка сдвинута вправо от края больше этого = начало абзаца
    short_line_mm: float = 10.0        # «короткая» последняя строка абзаца
    gap_factor: float = 2.6            # разрыв между строками > gap_factor * кегль = новый абзац


# --------------------------------------------------------------------------- всё вместе

@dataclass
class GostSettings:
    page: PageSettings = field(default_factory=PageSettings)
    page_number: PageNumberSettings = field(default_factory=PageNumberSettings)
    figure: FigureSettings = field(default_factory=FigureSettings)
    styles: dict[Kind, ElementStyle] = field(default_factory=default_styles)
    patterns: Patterns = field(default_factory=Patterns)
    tolerances: Tolerances = field(default_factory=Tolerances)
    heuristics: Heuristics = field(default_factory=Heuristics)

    # допустимые гарнитуры: достаточно вхождения в имя шрифта (пробелы и регистр не важны)
    font_names: tuple[str, ...] = ("Times New Roman",)
    # высота одинарной строки в кегле: для Times New Roman в Word это ~1,15
    single_line_height_em: float = 1.15
    # страницы, на которых не проверяем оформление текста (титульный лист); размер/поля проверяются всегда
    skip_pages: tuple[int, ...] = (1,)
    ignore_tables: bool = True         # не проверять текст внутри таблиц
