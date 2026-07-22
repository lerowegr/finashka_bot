import re

from app.scraper.schemas import ObshInfo

_RATING_RE = re.compile(r"Оценка общежития:[^0-9]{0,300}?(\d+(?:[.,]\d+)?)\s*/\s*10")


def parse_vuz_obsh(html: str) -> ObshInfo:
    dorm = None
    if "В этом вузе есть общежитие" in html:
        dorm = "not_all" if "дают не всем" in html else "yes"
    elif "нет общежития" in html:
        dorm = "no"

    m = _RATING_RE.search(html)
    rating = float(m.group(1).replace(",", ".")) if m else None
    return ObshInfo(dorm=dorm, dorm_rating=rating)
