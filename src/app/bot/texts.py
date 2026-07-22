"""Форматирование карточек. Telegram-специфика (HTML, лимит 4096) живёт только здесь."""

from html import escape

from app.db import models as m
from app.domain.services.profile import STATUS_EMOJI, STATUS_WORD
from app.scraper.schemas import FORM_RU, LEVEL_RU

MAIN_MENU = (
    "🎓 <b>Финашка-бот</b>\n\n"
    "Помогаю выбрать направление, вуз и программу.\n"
    "Данные — с tabiturient.ru, обновляются автоматически.\n\n"
    "Выберите раздел:"
)


def _cut(text: str | None, limit: int = 900) -> str | None:
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _fmt_money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def direction_card(direction: m.Direction, programs_count: int) -> str:
    parts = [
        f"<b>{escape(direction.name)}</b>",
        f"{direction.code} · {LEVEL_RU[direction.level]}",
        f"УГСН: {escape(direction.ugsn.name)}",
    ]
    scores = []
    if direction.min_score:
        scores.append(f"проходной от <b>{direction.min_score:g}</b>")
    if direction.avg_score:
        scores.append(f"средний <b>{direction.avg_score:g}</b>")
    if scores:
        parts.append("Баллы по России: " + ", ".join(scores))
    parts.append(f"Программ в вузах страны: <b>{programs_count}</b>")

    if description := _cut(direction.description):
        parts.append(f"\n📖 <b>О направлении</b>\n{escape(description)}")
    if career := _cut(direction.career):
        parts.append(f"\n💼 <b>Кем работать</b>\n{escape(career)}")
    return "\n".join(parts)


def university_card(vuz: m.University) -> str:
    tags = []
    if vuz.is_state is not None:
        tags.append("государственный" if vuz.is_state else "негосударственный")
    if vuz.is_branch:
        tags.append("филиал")
    if vuz.category:
        tags.append(f"категория {vuz.category}")

    parts = [
        f"🏛 <b>{escape(vuz.short_name)}</b>",
        escape(vuz.full_name),
        f"📍 {escape(vuz.region.name if vuz.region else 'регион неизвестен')}"
        + (f" · {', '.join(tags)}" if tags else ""),
    ]
    if vuz.avg_score:
        parts.append(f"Средневзвешенный проходной балл: <b>{vuz.avg_score:g}</b>")
    if vuz.budget_seats:
        parts.append(f"Бюджетных мест: <b>{vuz.budget_seats}</b>")

    dorm_text = {
        "yes": "есть",
        "not_all": "есть, но дают не всем",
        "no": "нет",
    }.get(vuz.dorm or "", "нет данных")
    if vuz.dorm_rating:
        dorm_text += f" (оценка {vuz.dorm_rating:g}/10)"
    parts.append(f"🏠 Общежитие: {dorm_text}")

    military = {True: "да", False: "нет"}.get(vuz.military_center, "нет данных")
    parts.append(f"🎖 Военный учебный центр: {military}")

    if description := _cut(vuz.description, 700):
        parts.append(f"\n{escape(description)}")

    if vuz.faculties:
        names = [f.name for f in vuz.faculties][:12]
        parts.append("\n<b>Структура вуза</b>\n" + "\n".join(f"· {escape(n)}" for n in names))
        if len(vuz.faculties) > 12:
            parts.append(f"…и ещё {len(vuz.faculties) - 12}")
    return "\n".join(parts)


def format_chance(status: str, total: int | None, pass_score: int | None) -> str | None:
    """Строка «ваши шансы» для карточки программы, или None если оценить нельзя."""
    if status == "unknown":
        return None
    emoji = STATUS_EMOJI[status]
    word = STATUS_WORD[status]
    if status == "missing":
        return f"🎯 Ваши шансы: {emoji} {word}"
    if total is not None and pass_score is not None:
        return f"🎯 Ваши шансы: {emoji} {word} (ваши {total} vs проходной {pass_score})"
    return f"🎯 Ваши шансы: {emoji} {word}"


def profile_text(overview: list[tuple[m.ExamSubject, int | None]]) -> str:
    lines = ["📊 <b>Мои баллы ЕГЭ</b>", ""]
    total = 0
    any_set = False
    for subject, score in overview:
        if score is not None:
            lines.append(f"• {escape(subject.name)}: <b>{score}</b>")
            total += score
            any_set = True
    if any_set:
        lines.append(f"\nСумма заданных: <b>{total}</b>")
    else:
        lines.append("Баллы ещё не заданы.")
    lines.append(
        "\nНажмите на предмет, чтобы указать балл. "
        "По ним в карточках программ показываются ваши шансы поступления."
    )
    return "\n".join(lines)


def program_card(program: m.Program, chance: tuple[str, int | None, int | None] | None = None) -> str:
    direction = program.direction
    parts = [
        f"📚 <b>{escape(direction.name)}</b>",
        f"{direction.code} · {LEVEL_RU[direction.level]}",
        f"🏛 {escape(program.university.short_name)} — "
        f"{escape(program.university.full_name)}",
    ]
    if program.profile:
        parts.append(f"Профиль: <b>{escape(program.profile)}</b>")
    if program.faculty:
        parts.append(f"Подразделение: {escape(program.faculty.name)}")

    required = sorted(e.subject.name for e in program.exams if e.kind == "required")
    choice = sorted(e.subject.name for e in program.exams if e.kind == "choice")
    if required:
        exams_line = " + ".join(escape(s) for s in required)
        if choice:
            exams_line += " + (" + " / ".join(escape(s) for s in choice) + ")"
        parts.append(f"\n💭 <b>ЕГЭ:</b> {exams_line}")

    for form in sorted(program.forms, key=lambda f: ("full", "evening", "extramural").index(f.form)):
        block = [f"\n📋 <b>{FORM_RU[form.form].capitalize()} форма</b>"]
        if form.pass_score:
            line = f"Проходной балл: <b>{form.pass_score}</b>"
            if form.pass_score_year:
                line += f" ({form.pass_score_year}"
                if form.pass_score_delta:
                    line += f", {form.pass_score_delta:+d} к прошлому году"
                line += ")"
            block.append(line)
        if form.budget_seats:
            seats = f"Бюджетных мест: <b>{form.budget_seats}</b>"
            if form.seats_main:
                seats += f" (основных {form.seats_main}, квоты {form.seats_quota or 0})"
            block.append(seats)
        if form.avg_enrolled_score:
            block.append(f"Средний балл зачисленных: {form.avg_enrolled_score:g}")
        if form.tuition:
            block.append(f"Стоимость: <b>{_fmt_money(form.tuition)} ₽/год</b>")
        if form.paid_only:
            block.append("Приём только на платной основе")
        parts.append("\n".join(block))

    if chance is None:
        parts.append(
            "\n🎯 Укажите свои баллы ЕГЭ (кнопка «📊 Мои баллы» в меню), чтобы видеть шансы."
        )
    else:
        line = format_chance(*chance)
        if line:
            parts.append("\n" + line)

    parts.append("\n<i>Данные: tabiturient.ru</i>")
    return "\n".join(parts)
