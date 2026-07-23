from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Float,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Уровни образования: 'bachelor' | 'specialist'
# Формы обучения:     'full' (очная) | 'evening' (очно-заочная) | 'extramural' (заочная)
# Общежитие:          'yes' | 'not_all' | 'no'


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class University(Base):
    __tablename__ = "university"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    short_name: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"))
    is_state: Mapped[bool | None] = mapped_column(Boolean)
    is_branch: Mapped[bool | None] = mapped_column(Boolean)
    category: Mapped[str | None] = mapped_column(Text)
    avg_score: Mapped[float | None] = mapped_column(Float)
    budget_seats: Mapped[int | None] = mapped_column(Integer)
    dorm: Mapped[str | None] = mapped_column(Text)
    dorm_rating: Mapped[float | None] = mapped_column(Float)
    military_center: Mapped[bool | None] = mapped_column(Boolean)  # seed, NULL = нет данных
    description: Mapped[str | None] = mapped_column(Text)  # seed из vuz.xlsx
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)

    region: Mapped["Region | None"] = relationship(lazy="joined")
    faculties: Mapped[list["Faculty"]] = relationship(back_populates="university")
    open_days: Mapped[list["OpenDay"]] = relationship(back_populates="university")
    directions: Mapped[list["UniversityDirection"]] = relationship(back_populates="university")


class Faculty(Base):
    __tablename__ = "faculty"
    __table_args__ = (UniqueConstraint("university_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(ForeignKey("university.id"))
    name: Mapped[str] = mapped_column(Text)

    university: Mapped["University"] = relationship(back_populates="faculties")


class Section(Base):
    """Раздел наук, например «Математические и естественные науки» (seed)."""

    __tablename__ = "section"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class Ugsn(Base):
    """Укрупнённая группа специальностей и направлений, код XX.00.00."""

    __tablename__ = "ugsn"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("section.id"))

    section: Mapped["Section | None"] = relationship(lazy="joined")


class Direction(Base):
    __tablename__ = "direction"

    id: Mapped[int] = mapped_column(primary_key=True)  # np-id сайта
    code: Mapped[str] = mapped_column(Text, unique=True)  # '01.03.01'
    name: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)  # 'bachelor' | 'specialist'
    ugsn_code: Mapped[str] = mapped_column(ForeignKey("ugsn.code"))
    description: Mapped[str | None] = mapped_column(Text)  # seed из spec.xlsx
    career: Mapped[str | None] = mapped_column(Text)  # seed «кем работать»
    min_score: Mapped[float | None] = mapped_column(Float)  # агрегаты /np/{id}
    avg_score: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)

    ugsn: Mapped["Ugsn"] = relationship(lazy="joined")


class UniversityDirection(Base):
    """Полный перечень направлений вуза (из /about). Направление в вузе — один раз."""

    __tablename__ = "university_direction"

    university_id: Mapped[int] = mapped_column(ForeignKey("university.id"), primary_key=True)
    direction_id: Mapped[int] = mapped_column(ForeignKey("direction.id"), primary_key=True)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)

    university: Mapped["University"] = relationship(back_populates="directions")
    direction: Mapped["Direction"] = relationship(lazy="joined")


class Program(Base):
    """Образовательная программа = вуз x направление x профиль."""

    __tablename__ = "program"
    __table_args__ = (
        Index("ix_program_univ", "university_id"),
        Index("ix_program_dir", "direction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)  # id сайта
    university_id: Mapped[int] = mapped_column(ForeignKey("university.id"))
    direction_id: Mapped[int] = mapped_column(ForeignKey("direction.id"))
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"))
    profile: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    detailed_at: Mapped[datetime | None] = mapped_column(DateTime)  # когда была разобрана карточка
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)

    university: Mapped["University"] = relationship(lazy="joined")
    direction: Mapped["Direction"] = relationship(lazy="joined")
    faculty: Mapped["Faculty | None"] = relationship(lazy="joined")
    forms: Mapped[list["ProgramForm"]] = relationship(back_populates="program")
    exams: Mapped[list["ProgramExam"]] = relationship(back_populates="program")


class ProgramForm(Base):
    __tablename__ = "program_form"

    program_id: Mapped[int] = mapped_column(ForeignKey("program.id"), primary_key=True)
    form: Mapped[str] = mapped_column(Text, primary_key=True)  # 'full'|'evening'|'extramural'
    pass_score: Mapped[int | None] = mapped_column(Integer)
    pass_score_year: Mapped[int | None] = mapped_column(Integer)
    pass_score_delta: Mapped[int | None] = mapped_column(Integer)
    budget_seats: Mapped[int | None] = mapped_column(Integer)
    seats_main: Mapped[int | None] = mapped_column(Integer)
    seats_quota: Mapped[int | None] = mapped_column(Integer)  # особая+отдельная+целевая суммарно
    avg_enrolled_score: Mapped[float | None] = mapped_column(Float)
    tuition: Mapped[int | None] = mapped_column(Integer)  # руб/год
    paid_only: Mapped[bool] = mapped_column(Boolean, default=False)

    program: Mapped["Program"] = relationship(back_populates="forms")


class ExamSubject(Base):
    __tablename__ = "exam_subject"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class ProgramExam(Base):
    __tablename__ = "program_exam"

    program_id: Mapped[int] = mapped_column(ForeignKey("program.id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("exam_subject.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # 'required' | 'choice'

    program: Mapped["Program"] = relationship(back_populates="exams")
    subject: Mapped["ExamSubject"] = relationship(lazy="joined")


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)


class Favorite(Base):
    __tablename__ = "favorite"

    tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)  # 'direction'|'university'|'program'
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserScore(Base):
    """Волна 2: профиль «Мои баллы ЕГЭ» — таблица заложена сразу."""

    __tablename__ = "user_score"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 100"),)

    tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("exam_subject.id"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer)


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    params: Mapped[str] = mapped_column(Text)  # JSON фильтров
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScrapeRun(Base):
    __tablename__ = "scrape_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # 'light'|'full'|'np'|'seed'
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    pages_ok: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str | None] = mapped_column(Text)  # 'ok'|'partial'|'failed'


class OpenDay(Base):
    """День открытых дверей вуза (парсится с /vuzu/{slug}/dod)."""

    __tablename__ = "open_day"
    __table_args__ = (Index("ix_open_day_univ", "university_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(ForeignKey("university.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    title: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)

    university: Mapped["University"] = relationship(back_populates="open_days")


class ChangeLog(Base):
    """Диффы обходов — фундамент уведомлений волны 3."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(Text)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    scrape_run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_run.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
