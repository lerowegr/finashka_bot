"""Список вузов региона со страницы /city/{slug}.

Слаг вуза надёжно зашит в имя файла логотипа: logovuz/{slug}.png.
"""

import re

_SLUG_RE = re.compile(r'logovuz/([a-z0-9_-]+)\.png"\s+class="vuzlistimg"')


def parse_city_slugs(html: str) -> list[str]:
    """Слаги вузов города в порядке появления, без повторов."""
    slugs: list[str] = []
    for match in _SLUG_RE.finditer(html):
        slug = match.group(1)
        if slug not in slugs:
            slugs.append(slug)
    return slugs
