"""Перевод единиц. В PDF координаты в пунктах (pt), в настройках всё в миллиметрах."""

PT_PER_MM = 72 / 25.4


def mm_to_pt(mm: float) -> float:
    return mm * PT_PER_MM


def pt_to_mm(pt: float) -> float:
    return pt / PT_PER_MM
