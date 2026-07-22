"""Полная карточка программы /program/n?{id}: формы обучения, места, стоимость."""

import re

from app.scraper.parsers.common import parse_tree, to_float, to_int
from app.scraper.schemas import (
    LEVEL_MAP,
    ExamSet,
    ProgramCard,
    ProgramFormInfo,
    canon_subject,
)

_FORM_MARKERS = [
    ("Очная форма обучения", "full"),
    ("Очно-заочная форма обучения", "evening"),
    ("Заочная форма обучения", "extramural"),
    # опечатка на сайте — встречается в блоке «формы не представлены»
    ("Зочная форма обучения", "extramural"),
]

_SCORE_RE = re.compile(r"(\d{2,3})\s+(-?\d{1,3}\s+)?Проходной балл\s+на[^0-9]{0,40}(\d{4})\s+году")
_SEATS_RE = re.compile(r"(\d{1,5})\s+Бюджетных мест")
_QUOTA_RE = re.compile(
    r"((?:\d{1,4}\s+){3}\d{1,4})\s+основные места\s+особая квота\s+отдельная квота\s+целевая квота"
)
_AVG_RE = re.compile(r"(\d{2,3}(?:[.,]\d+)?)\s+средний балл ЕГЭ")
_TUITION_RE = re.compile(r"Стоимость обучения\s*-\s*([\d\s]+)\s*рублей за год")
_FIELD_RES = {
    "faculty": re.compile(r"Подразделение:\s*(.+?)\s*Субъект:"),
    "direction_code": re.compile(r"Код программы:\s*(\d{2}\.\d{2}\.\d{2})"),
    "level_ru": re.compile(r"Уровень программы:\s*(Бакалавриат|Специалитет)"),
    "profile": re.compile(r"Профиль программы:\s*(.+?)\s*Вступительные ЕГЭ"),
}


def _text_lines(html: str) -> list[str]:
    """Плоский текст страницы построчно (теги -> переводы строк)."""
    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", no_script)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_exams_from_lines(lines: list[str]) -> ExamSet:
    required: list[str] = []
    choice: list[str] = []
    bucket: list[str] | None = None
    for line in lines:
        if line.startswith("Обязательные ЕГЭ"):
            bucket = required
        elif line.startswith("ЕГЭ по выбору"):
            bucket = choice
        elif line.startswith("Дополнительные баллы") or line.endswith("форма обучения"):
            if bucket is choice or line.startswith("Дополнительные баллы"):
                break
            bucket = None
        elif bucket is not None:
            subj = canon_subject(line)
            if subj and subj not in bucket:
                bucket.append(subj)
    return ExamSet(required=required, choice=choice)


def _parse_form_section(form: str, section: str) -> ProgramFormInfo:
    info = ProgramFormInfo(form=form)

    m = _SCORE_RE.search(section)
    if m:
        info.pass_score = int(m.group(1))
        info.pass_score_delta = int(m.group(2)) if m.group(2) else None
        info.pass_score_year = int(m.group(3))

    m = _SEATS_RE.search(section)
    if m:
        info.budget_seats = int(m.group(1))

    m = _QUOTA_RE.search(section)
    if m:
        numbers = [int(n) for n in m.group(1).split()]
        # столбец основных мест на сайте — самый широкий, число в нём максимально;
        # надёжно берём максимум, остальное суммируем как квоты
        info.seats_main = max(numbers)
        numbers.remove(info.seats_main)
        info.seats_quota = sum(numbers)

    m = _AVG_RE.search(section)
    if m:
        info.avg_enrolled_score = to_float(m.group(1))

    m = _TUITION_RE.search(section)
    if m:
        info.tuition = to_int(m.group(1))

    info.paid_only = "только на платной основе" in section
    return info


def parse_program_card(html: str, program_id: int) -> ProgramCard:
    lines = _text_lines(html)
    flat = " ".join(lines)

    fields: dict[str, str | None] = {}
    for key, rx in _FIELD_RES.items():
        m = rx.search(flat)
        fields[key] = m.group(1).strip() if m else None

    profile = fields["profile"]
    if profile and profile.lower() == "без профиля":
        profile = None

    # разрезаем плоский текст на секции по маркерам форм обучения
    positions = []
    for marker, form in _FORM_MARKERS:
        for m in re.finditer(marker, flat):
            positions.append((m.start(), form, marker))
    positions.sort()

    forms: list[ProgramFormInfo] = []
    seen: set[str] = set()
    for i, (pos, form, marker) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(flat)
        section = flat[pos:end]
        if form in seen or "не представлен" in section[: len(marker) + 80]:
            continue
        seen.add(form)
        parsed = _parse_form_section(form, section)
        if parsed.pass_score or parsed.budget_seats or parsed.tuition or parsed.paid_only:
            forms.append(parsed)

    return ProgramCard(
        id=program_id,
        direction_code=fields["direction_code"],
        level=LEVEL_MAP.get(fields["level_ru"] or ""),
        profile=profile,
        faculty=fields["faculty"],
        exams=_parse_exams_from_lines(lines),
        forms=forms,
    )
