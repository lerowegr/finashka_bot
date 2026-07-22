import re

from app.scraper.schemas import SitemapIndex

_VUZ_RE = re.compile(r"<loc>https://tabiturient\.ru/vuzu/([a-z0-9_-]+)</loc>")
_NP_RE = re.compile(r"<loc>https://tabiturient\.ru/np/(\d+)</loc>")
_PROGRAM_RE = re.compile(r"<loc>https://tabiturient\.ru/program/n\?(\d+)</loc>")


def parse_sitemap(xml: str) -> SitemapIndex:
    """Sitemap — готовый реестр всех сущностей сайта, обход ничего не «ищет»."""
    return SitemapIndex(
        vuz_slugs=sorted(set(_VUZ_RE.findall(xml))),
        np_ids=sorted({int(m) for m in _NP_RE.findall(xml)}),
        program_ids=sorted({int(m) for m in _PROGRAM_RE.findall(xml)}),
    )
