"""Карточки программ из списков: /vuzu/{slug}/proxodnoi и /np/{id}."""

import logging
import re

from selectolax.parser import Node

from app.scraper.parsers.common import node_text, parse_tree
from app.scraper.schemas import LEVEL_MAP, ExamSet, PassScore, ProgramSummary, canon_subject

log = logging.getLogger(__name__)

_CODE_RE = re.compile(r"(Бакалавриат|Специалитет)\s*\|\s*(\d{2}\.\d{2}\.\d{2})")
_PROFILE_RE = re.compile(r"Профиль:\s*(.+?)\s*(?:Вуз:|Подразделение:|Набор экзаменов:)")
_FACULTY_RE = re.compile(r"Подразделение:\s*(.+?)\s*(?:Набор экзаменов:|Проходные баллы:)")
_YEAR_RE = re.compile(r"в\s+(\d{4})\s+году")

_FORM_LABELS = [  # порядок важен: сначала более специфичные префиксы
    ("очно-заоч", "evening"),
    ("вечер", "evening"),
    ("заоч", "extramural"),
    ("очно", "full"),
]


def _form_from_label(label: str) -> str | None:
    label = label.lower()
    for prefix, form in _FORM_LABELS:
        if label.startswith(prefix):
            return form
    return None


def _parse_exams(card: Node) -> ExamSet:
    required: list[str] = []
    choice: list[str] = []
    for info in card.css("div.dopinfodiv"):
        text = node_text(info)
        subject_node = info.css_first("b")
        if subject_node is None:
            continue
        if text.startswith("Обязательный ЕГЭ"):
            subj = canon_subject(node_text(subject_node))
            if subj and subj not in required:
                required.append(subj)
        elif text.startswith("ЕГЭ на выбор"):
            for raw in node_text(subject_node).split(" или "):
                subj = canon_subject(raw)
                if subj and subj not in choice:
                    choice.append(subj)
    return ExamSet(required=required, choice=choice)


def _parse_pass_scores(card: Node) -> list[PassScore]:
    scores: list[PassScore] = []
    for cell in card.css("table.circ2unique"):
        score_node = cell.css_first("b")
        form_node = cell.css_first("span.font0")
        if score_node is None or form_node is None:
            continue
        raw_score = node_text(score_node)
        form = _form_from_label(node_text(form_node))
        if not raw_score.isdigit() or form is None:
            continue
        # год — в подсказке соседнего dopinfodiv («…в 2025 году»)
        year = None
        parent = cell.parent
        for _ in range(6):
            if parent is None:
                break
            hint = parent.css_first("div.dopinfodiv")
            if hint is not None and "Проходной балл" in node_text(hint):
                m = _YEAR_RE.search(node_text(hint))
                if m:
                    year = int(m.group(1))
                break
            parent = parent.parent
        try:
            scores.append(PassScore(form=form, score=int(raw_score), year=year))
        except ValueError:
            log.warning("отброшен неправдоподобный балл %s", raw_score)
    return scores


def parse_program_cards(html: str) -> list[ProgramSummary]:
    tree = parse_tree(html)
    programs: list[ProgramSummary] = []
    for card in tree.css("div.mobpaddcard"):
        elem_id = card.attributes.get("id") or ""
        if not elem_id.startswith("elem"):
            continue
        text = node_text(card)
        m = _CODE_RE.search(text)
        name_node = card.css_first("span.font2 b")
        if not m or name_node is None:
            log.warning("карточка %s без кода/названия — пропущена", elem_id)
            continue

        profile_m = _PROFILE_RE.search(text)
        faculty_m = _FACULTY_RE.search(text)
        profile = profile_m.group(1) if profile_m else None
        if profile and profile.lower() == "без профиля":
            profile = None

        programs.append(
            ProgramSummary(
                id=int(elem_id.removeprefix("elem")),
                name=node_text(name_node),
                level=LEVEL_MAP[m.group(1)],
                direction_code=m.group(2),
                profile=profile,
                faculty=faculty_m.group(1) if faculty_m else None,
                exams=_parse_exams(card),
                pass_scores=_parse_pass_scores(card),
                paid_only="только на платной основе" in text,
            )
        )
    return programs
