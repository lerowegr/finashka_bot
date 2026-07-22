import re

from app.scraper.parsers.common import node_text, parse_tree, to_float, to_int
from app.scraper.schemas import LEVEL_MAP, DirectionRef, VuzAbout

_DIR_RE = re.compile(r"^(\d{2}\.\d{2}\.\d{2})\s*\|\s*(Бакалавриат|Специалитет)\s+(.+)$")
_UGSN_RE = re.compile(
    r'text-transform:uppercase;[^"]*">([^<]+)</b></span>\s*(?:<br>)?\s*'
    r'<span[^>]*class="font1"[^>]*>Укрупненная группа (\d{2}\.00\.00)</span>'
)
_FACULTY_RE = re.compile(r"Структура вуза</b>\s*<ul class=\"font2\">(.*?)</ul>", re.S)

_STAT_LABELS = {
    "направлений подготовки": "directions_count",
    "образовательных программ": "programs_count",
    "бюджетных мест": "budget_seats",
    "средневзвешенный проходной балл": "avg_score",
}


def parse_vuz_about(html: str, slug: str) -> VuzAbout:
    tree = parse_tree(html)

    short_name = node_text(tree.css_first('h2[itemprop="alternateName"]'))
    full_name = node_text(tree.css_first('h2[itemprop="name"]'))

    region_slug = region_name = None
    for a in tree.css('a[href*="/city/"]'):
        name = node_text(a.css_first("b.font1"))
        if name:
            region_slug = a.attributes.get("href", "").rstrip("/").rsplit("/", 1)[-1]
            region_name = name
            break

    is_state = is_branch = None
    for tag in tree.css("table.tag2 b.font1"):
        t = node_text(tag)
        if "вуз" in t.lower():
            is_state = t.lower().startswith("гос")
        elif t in ("Головной", "Филиал"):
            is_branch = t == "Филиал"

    category = None
    cat_node = tree.css_first('td.ocenka a[href*="globalrating"] b.font5')
    if cat_node is not None:
        cat = node_text(cat_node)
        if len(cat) <= 2:
            category = cat

    stats: dict[str, float | int | None] = {}
    for td in tree.css("td"):
        value_node = td.css_first("b.font5")
        label_node = td.css_first("span.font2")
        if value_node is None or label_node is None:
            continue
        field = _STAT_LABELS.get(node_text(label_node).lower())
        if field and field not in stats:
            raw = node_text(value_node)
            stats[field] = to_float(raw) if field == "avg_score" else to_int(raw)

    directions: list[DirectionRef] = []
    seen_np: set[int] = set()
    for a in tree.css('a[href*="/proxodnoi?"]'):
        href = a.attributes.get("href", "")
        np_part = href.rsplit("?", 1)[-1]
        if not np_part.isdigit():
            continue
        m = _DIR_RE.match(node_text(a))
        if not m or int(np_part) in seen_np:
            continue
        seen_np.add(int(np_part))
        directions.append(
            DirectionRef(
                np_id=int(np_part),
                code=m.group(1),
                level=LEVEL_MAP[m.group(2)],
                name=m.group(3).strip(),
            )
        )

    ugsn_names = {code: name.strip() for name, code in _UGSN_RE.findall(html)}

    faculties: list[str] = []
    fac_match = _FACULTY_RE.search(html)
    if fac_match:
        faculties = [
            f.strip() for f in re.findall(r"<li>(.*?)</li>", fac_match.group(1)) if f.strip()
        ]

    return VuzAbout(
        slug=slug,
        short_name=short_name or slug.upper(),
        full_name=full_name or short_name or slug,
        region_slug=region_slug,
        region_name=region_name,
        is_state=is_state,
        is_branch=is_branch,
        category=category,
        directions=directions,
        faculties=faculties,
        ugsn_names=ugsn_names,
        **stats,
    )
