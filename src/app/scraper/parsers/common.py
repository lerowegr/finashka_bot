import re

from selectolax.parser import HTMLParser, Node


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def node_text(node: Node | None, sep: str = " ") -> str:
    if node is None:
        return ""
    return norm(node.text(separator=sep, strip=True))


def to_int(s: str | None) -> int | None:
    if not s:
        return None
    digits = re.sub(r"[^\d-]", "", s)
    try:
        return int(digits)
    except ValueError:
        return None


def to_float(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    return float(m.group().replace(",", ".")) if m else None


def parse_tree(html: str) -> HTMLParser:
    return HTMLParser(html)
