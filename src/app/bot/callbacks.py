"""Единый реестр CallbackData: уникальные префиксы, стабильные id вместо индексов."""

from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="m"):
    to: str  # 'main' | 'catalog' | 'ege' | 'regions' | 'favs'


class LevelCb(CallbackData, prefix="lvl"):
    level: str  # 'bachelor' | 'specialist'


class SectionCb(CallbackData, prefix="sec"):
    level: str
    section_id: int


class UgsnCb(CallbackData, prefix="ug"):
    level: str
    section_id: int
    ugsn: str


class DirCb(CallbackData, prefix="dir"):
    dir_id: int


class DirProgsCb(CallbackData, prefix="dp"):
    dir_id: int
    page: int
    ege: bool = False  # фильтровать по выбранным предметам из FSM


class SubjToggleCb(CallbackData, prefix="st"):
    subject_id: int


class EgeSearchCb(CallbackData, prefix="eg"):
    page: int


class EgePickerCb(CallbackData, prefix="egp"):
    """Вернуться к выбору предметов, сохранив уже отмеченные (из FSM)."""


class RegionsCb(CallbackData, prefix="rg"):
    page: int


class RegionCb(CallbackData, prefix="rv"):
    region_id: int
    page: int


class VuzCb(CallbackData, prefix="vz"):
    univ_id: int


class VuzProgsCb(CallbackData, prefix="vp"):
    univ_id: int
    page: int


class ProgCb(CallbackData, prefix="pg"):
    prog_id: int


class FavToggleCb(CallbackData, prefix="ft"):
    kind: str  # 'direction' | 'university' | 'program'
    item_id: int


class ProfileCb(CallbackData, prefix="prof"):
    action: str  # 'clear'


class ScoreSubjCb(CallbackData, prefix="scs"):
    subject_id: int


class NoopCb(CallbackData, prefix="noop"):
    pass
