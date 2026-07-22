"""Дни открытых дверей вуза: /vuzu/{slug}/dod.

На странице кроме собственных ДОД вуза есть боковые блоки (вопросы и анонсы
других вузов) — берём только события из основного контейнера div.content.
"""

import re
from datetime import date, datetime

from app.scraper.parsers.common import norm, parse_tree
from app.scraper.schemas import OpenDayInfo

_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
_DATE_RE = re.compile(r"(\d{1,2})\s+([а-яё]+)")
_TIME_RE = re.compile(r"в\s+(\d{1,2}):(\d{2})")
_ADDR_RE = re.compile(
    r"облас|край|Республик|Москва|Санкт-Петербург|\bг\.|\bул\.|\bпр\.|шоссе|"
    r"переул|проспект|наб\.|Онлайн|д\.\s*\d"
)


def parse_vuz_dod(html: str, today: date | None = None) -> list[OpenDayInfo]:
    today = today or date.today()
    tree = parse_tree(html)
    events: list[OpenDayInfo] = []

    for table in tree.css("div.content table.dodlist"):
        cells = table.css("td")
        if not cells:
            continue
        head = norm(cells[0].text(separator=" ", strip=True))
        date_match = _DATE_RE.search(head)
        if not date_match or date_match.group(2) not in _MONTHS:
            continue

        day = int(date_match.group(1))
        month = _MONTHS[date_match.group(2)]
        time_match = _TIME_RE.search(head)
        hour, minute = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (0, 0)

        # год не указан на странице — выводим из ближайшей будущей даты
        year = today.year
        if (date(year, month, day) - today).days < -14:
            year += 1
        starts_at = datetime(year, month, day, hour, minute)

        lines: list[str] = []
        for raw in table.text(separator="\n", strip=True).split("\n"):
            line = norm(raw)
            if not line or line == "Подробнее" or line == head:
                continue
            if _DATE_RE.fullmatch(line) or _TIME_RE.fullmatch(line):
                continue
            if line not in lines:
                lines.append(line)

        location = next((line for line in lines if _ADDR_RE.search(line)), None)
        titles = [line for line in lines if line != location]
        # заголовок = самая содержательная строка (у части вузов это описание, а не короткий тайтл)
        title = max(titles, key=len) if titles else "День открытых дверей"

        events.append(OpenDayInfo(starts_at=starts_at, title=title[:200], location=location))

    return events
