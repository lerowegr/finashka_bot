"""Чистые построители клавиатур: принимают готовые данные, БД не трогают."""

import math
from collections.abc import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import (
    DirCb,
    DirProgsCb,
    EgePickerCb,
    EgeSearchCb,
    FavToggleCb,
    LevelCb,
    CompareCb,
    CompareStartCb,
    MenuCb,
    NoopCb,
    ProfileCb,
    ProgCb,
    RegionCb,
    RegionsCb,
    ScoreSubjCb,
    SectionCb,
    SubjToggleCb,
    UgsnCb,
    VuzCb,
    VuzProgsCb,
)
from app.db import models as m

PER_PAGE = 8
REGIONS_PER_PAGE = 10


def _home() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCb(to="main").pack())


def _pager(
    kb: InlineKeyboardBuilder,
    page_cb: Callable[[int], object],
    page: int,
    total: int,
    per_page: int = PER_PAGE,
) -> None:
    pages = math.ceil(total / per_page) if total else 1
    if pages <= 1:
        return
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀", callback_data=page_cb(page - 1).pack()))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data=NoopCb().pack()))
    if page + 1 < pages:
        row.append(InlineKeyboardButton(text="▶", callback_data=page_cb(page + 1).pack()))
    kb.row(*row)


def _fav_text(is_fav: bool) -> str:
    return "★ В избранном" if is_fav else "☆ В избранное"


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎓 По уровню образования", callback_data=MenuCb(to="catalog").pack()))
    kb.row(InlineKeyboardButton(text="📊 Мои баллы ЕГЭ", callback_data=MenuCb(to="profile").pack()))
    kb.row(InlineKeyboardButton(text="💭 Поиск по предметам ЕГЭ", callback_data=MenuCb(to="ege").pack()))
    kb.row(InlineKeyboardButton(text="🏛 ВУЗы по регионам", callback_data=MenuCb(to="regions").pack()))
    kb.row(InlineKeyboardButton(text="⭐ Избранное", callback_data=MenuCb(to="favs").pack()))
    return kb.as_markup()


def profile_kb(overview: list[tuple[m.ExamSubject, int | None]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for subject, score in overview:
        mark = f": {score}" if score is not None else ": —"
        kb.row(
            InlineKeyboardButton(
                text=f"{subject.name}{mark}",
                callback_data=ScoreSubjCb(subject_id=subject.id).pack(),
            )
        )
    kb.row(InlineKeyboardButton(text="🗑 Очистить всё", callback_data=ProfileCb(action="clear").pack()))
    kb.row(_home())
    return kb.as_markup()


def cancel_score_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀ Назад к баллам", callback_data=MenuCb(to="profile").pack()))
    return kb.as_markup()


def levels_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Бакалавриат", callback_data=LevelCb(level="bachelor").pack()))
    kb.row(InlineKeyboardButton(text="Специалитет", callback_data=LevelCb(level="specialist").pack()))
    kb.row(_home())
    return kb.as_markup()


def sections_kb(level: str, sections: list[tuple[int, str, int]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for section_id, name, count in sections:
        kb.row(
            InlineKeyboardButton(
                text=f"{name} ({count})",
                callback_data=SectionCb(level=level, section_id=section_id).pack(),
            )
        )
    kb.row(InlineKeyboardButton(text="◀ Назад", callback_data=MenuCb(to="catalog").pack()))
    kb.row(_home())
    return kb.as_markup()


def ugsns_kb(level: str, section_id: int, ugsns: list[tuple[str, str, int]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name, count in ugsns:
        kb.row(
            InlineKeyboardButton(
                text=f"{code} {name} ({count})",
                callback_data=UgsnCb(level=level, section_id=section_id, ugsn=code).pack(),
            )
        )
    kb.row(InlineKeyboardButton(text="◀ Назад", callback_data=LevelCb(level=level).pack()))
    kb.row(_home())
    return kb.as_markup()


def directions_kb(
    level: str, section_id: int, directions: list[m.Direction]
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in directions:
        kb.row(
            InlineKeyboardButton(text=f"{d.code} {d.name}", callback_data=DirCb(dir_id=d.id).pack())
        )
    kb.row(
        InlineKeyboardButton(
            text="◀ Назад", callback_data=SectionCb(level=level, section_id=section_id).pack()
        )
    )
    kb.row(_home())
    return kb.as_markup()


def direction_card_kb(
    direction: m.Direction, is_fav: bool, has_programs: bool, back_cb
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_programs:
        kb.row(
            InlineKeyboardButton(
                text="🏛 Вузы с этим направлением",
                callback_data=DirProgsCb(dir_id=direction.id, page=0, ege=False).pack(),
            )
        )
    kb.row(
        InlineKeyboardButton(
            text=_fav_text(is_fav),
            callback_data=FavToggleCb(kind="direction", item_id=direction.id).pack(),
        )
    )
    if back_cb is not None:
        kb.row(InlineKeyboardButton(text="◀ Назад", callback_data=back_cb.pack()))
    kb.row(_home())
    return kb.as_markup()


def programs_list_kb(
    items: list[m.Program],
    page: int,
    total: int,
    page_cb: Callable[[int], object],
    back_cb,
    label: Callable[[m.Program], str],
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for program in items:
        kb.row(InlineKeyboardButton(text=label(program), callback_data=ProgCb(prog_id=program.id).pack()))
    _pager(kb, page_cb, page, total)
    if back_cb is not None:
        kb.row(InlineKeyboardButton(text="◀ Назад", callback_data=back_cb.pack()))
    kb.row(_home())
    return kb.as_markup()


def program_card_kb(program: m.Program, is_fav: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text=_fav_text(is_fav),
            callback_data=FavToggleCb(kind="program", item_id=program.id).pack(),
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="🏛 О вузе", callback_data=VuzCb(univ_id=program.university_id).pack()
        )
    )
    kb.row(_home())
    return kb.as_markup()


def subjects_kb(subjects: list[m.ExamSubject], selected_ids: set[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(
            text=f"{'✅ ' if s.id in selected_ids else ''}{s.name}",
            callback_data=SubjToggleCb(subject_id=s.id).pack(),
        )
        for s in subjects
    ]
    kb.add(*buttons)
    kb.adjust(2)
    kb.row(
        InlineKeyboardButton(
            text="🔎 Искать направления", callback_data=EgeSearchCb(page=0).pack()
        )
    )
    kb.row(_home())
    return kb.as_markup()


def ege_results_kb(
    results: list[tuple[m.Direction, int]], page: int, total: int
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for direction, count in results:
        kb.row(
            InlineKeyboardButton(
                text=f"{direction.code} {direction.name} ({count})",
                callback_data=DirProgsCb(dir_id=direction.id, page=0, ege=True).pack(),
            )
        )
    _pager(kb, lambda p: EgeSearchCb(page=p), page, total)
    kb.row(
        InlineKeyboardButton(
            text="◀ К выбору предметов", callback_data=EgePickerCb().pack()
        )
    )
    kb.row(_home())
    return kb.as_markup()


def regions_kb(
    regions_page: list[tuple[int, str, int]], page: int, total: int, per_page: int
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for region_id, name, count in regions_page:
        kb.row(
            InlineKeyboardButton(
                text=f"{name} ({count})",
                callback_data=RegionCb(region_id=region_id, page=0).pack(),
            )
        )
    _pager(kb, lambda p: RegionsCb(page=p), page, total, per_page)
    kb.row(_home())
    return kb.as_markup()


def universities_kb(
    items: list[m.University], page: int, total: int, region_id: int
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in items:
        score = f" · {u.avg_score:g}" if u.avg_score else ""
        kb.row(InlineKeyboardButton(text=f"{u.short_name}{score}", callback_data=VuzCb(univ_id=u.id).pack()))
    _pager(kb, lambda p: RegionCb(region_id=region_id, page=p), page, total)
    kb.row(InlineKeyboardButton(text="◀ К регионам", callback_data=MenuCb(to="regions").pack()))
    kb.row(_home())
    return kb.as_markup()


def university_card_kb(university: m.University, is_fav: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="📚 Программы вуза", callback_data=VuzProgsCb(univ_id=university.id, page=0).pack()
        )
    )
    kb.row(
        InlineKeyboardButton(
            text=_fav_text(is_fav),
            callback_data=FavToggleCb(kind="university", item_id=university.id).pack(),
        ),
        InlineKeyboardButton(
            text="⚖ Сравнить", callback_data=CompareStartCb(a=university.id).pack()
        ),
    )
    if university.region_id:
        kb.row(
            InlineKeyboardButton(
                text="◀ К вузам региона",
                callback_data=RegionCb(region_id=university.region_id, page=0).pack(),
            )
        )
    kb.row(_home())
    return kb.as_markup()


def compare_candidates_kb(a_id: int, candidates: list[m.University]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in candidates:
        kb.row(
            InlineKeyboardButton(
                text=f"🅱 {u.short_name}", callback_data=CompareCb(a=a_id, b=u.id).pack()
            )
        )
    kb.row(InlineKeyboardButton(text="◀ Назад", callback_data=VuzCb(univ_id=a_id).pack()))
    kb.row(_home())
    return kb.as_markup()


def compare_result_kb(a_id: int, b_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🅰 О вузе", callback_data=VuzCb(univ_id=a_id).pack()),
        InlineKeyboardButton(text="🅱 О вузе", callback_data=VuzCb(univ_id=b_id).pack()),
    )
    kb.row(
        InlineKeyboardButton(
            text="⚖ Другой вуз для сравнения", callback_data=CompareStartCb(a=a_id).pack()
        )
    )
    kb.row(_home())
    return kb.as_markup()


def favorites_kb(grouped: dict[str, list]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in grouped["direction"]:
        kb.row(InlineKeyboardButton(text=f"🎓 {d.code} {d.name}", callback_data=DirCb(dir_id=d.id).pack()))
    for u in grouped["university"]:
        kb.row(InlineKeyboardButton(text=f"🏛 {u.short_name}", callback_data=VuzCb(univ_id=u.id).pack()))
    for p in grouped["program"]:
        kb.row(
            InlineKeyboardButton(
                text=f"📚 {p.direction.name} — {p.university.short_name}",
                callback_data=ProgCb(prog_id=p.id).pack(),
            )
        )
    kb.row(_home())
    return kb.as_markup()
