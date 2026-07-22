"""DTO границы «сайт → наша система». Валидация здесь защищает БД от битых страниц."""

from pydantic import BaseModel, Field

LEVEL_MAP = {"Бакалавриат": "bachelor", "Специалитет": "specialist"}
LEVEL_RU = {"bachelor": "Бакалавриат", "specialist": "Специалитет"}
FORM_RU = {"full": "очная", "evening": "очно-заочная", "extramural": "заочная"}

# Полный словарь предметов, встречающихся на сайте (Этап 3 аудита)
SUBJECTS = [
    "Русский язык",
    "Математика",
    "Обществознание",
    "ИКТ",
    "Иностранный язык",
    "Биология",
    "География",
    "Химия",
    "Физика",
    "Литература",
    "История",
    "ДВИ",
]
SUBJECT_ALIASES = {
    "Информатика": "ИКТ",
    "Дополнительный экзамен": "ДВИ",
    "Профильная математика": "Математика",
}


def canon_subject(raw: str) -> str | None:
    s = raw.strip().rstrip(".")
    s = SUBJECT_ALIASES.get(s, s)
    return s if s in SUBJECTS else None


class DirectionRef(BaseModel):
    np_id: int
    code: str = Field(pattern=r"^\d{2}\.\d{2}\.\d{2}$")
    level: str  # 'bachelor' | 'specialist'
    name: str = Field(min_length=2)


class VuzAbout(BaseModel):
    slug: str
    short_name: str
    full_name: str
    region_slug: str | None = None
    region_name: str | None = None
    is_state: bool | None = None
    is_branch: bool | None = None
    category: str | None = None
    directions_count: int | None = None
    programs_count: int | None = None
    budget_seats: int | None = None
    avg_score: float | None = Field(default=None, ge=0, le=500)
    directions: list[DirectionRef] = []
    faculties: list[str] = []
    ugsn_names: dict[str, str] = {}  # '06.00.00' -> 'БИОЛОГИЧЕСКИЕ НАУКИ'


class ExamSet(BaseModel):
    required: list[str] = []
    choice: list[str] = []


class PassScore(BaseModel):
    form: str  # 'full' | 'evening' | 'extramural'
    score: int = Field(ge=0, le=500)
    year: int | None = Field(default=None, ge=2015, le=2035)


class ProgramSummary(BaseModel):
    """Карточка программы из списка (/vuzu/{slug}/proxodnoi или /np/{id})."""

    id: int
    name: str
    level: str
    direction_code: str = Field(pattern=r"^\d{2}\.\d{2}\.\d{2}$")
    profile: str | None = None
    faculty: str | None = None
    exams: ExamSet = ExamSet()
    pass_scores: list[PassScore] = []
    paid_only: bool = False


class ProgramFormInfo(BaseModel):
    form: str
    pass_score: int | None = Field(default=None, ge=0, le=500)
    pass_score_year: int | None = None
    pass_score_delta: int | None = None
    budget_seats: int | None = None
    seats_main: int | None = None
    seats_quota: int | None = None
    avg_enrolled_score: float | None = Field(default=None, ge=0, le=500)
    tuition: int | None = Field(default=None, ge=0)
    paid_only: bool = False


class ProgramCard(BaseModel):
    """Полная карточка /program/n?{id}."""

    id: int
    direction_code: str | None = None
    level: str | None = None
    profile: str | None = None
    faculty: str | None = None
    exams: ExamSet = ExamSet()
    forms: list[ProgramFormInfo] = []


class ObshInfo(BaseModel):
    dorm: str | None = None  # 'yes' | 'not_all' | 'no'
    dorm_rating: float | None = Field(default=None, ge=0, le=10)


class NpAggregates(BaseModel):
    np_id: int
    min_score: float | None = Field(default=None, ge=0, le=500)
    avg_score: float | None = Field(default=None, ge=0, le=500)
    programs: list[ProgramSummary] = []


class SitemapIndex(BaseModel):
    vuz_slugs: list[str]
    np_ids: list[int]
    program_ids: list[int]
