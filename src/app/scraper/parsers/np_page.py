"""Страница направления /np/{id}: агрегаты по России + программы всех вузов."""

import re

from app.scraper.parsers.programs_list import parse_program_cards
from app.scraper.schemas import NpAggregates

_MIN_RE = re.compile(r"Проходной балл\s*-\s*от\s*(\d+(?:[.,]\d+)?)")
_AVG_RE = re.compile(r"Средний проходной балл\s*-\s*(\d+(?:[.,]\d+)?)")


def _grab(rx: re.Pattern, text: str) -> float | None:
    m = rx.search(text)
    return float(m.group(1).replace(",", ".")) if m else None


def parse_np_page(html: str, np_id: int) -> NpAggregates:
    flat = re.sub(r"<[^>]+>", " ", html)
    flat = re.sub(r"\s+", " ", flat)
    return NpAggregates(
        np_id=np_id,
        min_score=_grab(_MIN_RE, flat),
        avg_score=_grab(_AVG_RE, flat),
        programs=parse_program_cards(html),
    )
