from app.scraper.parsers.city import parse_city_slugs


def test_moscow_city_slugs(load_fixture):
    slugs = parse_city_slugs(load_fixture("city_moscow.html"))
    # на странице города перечислены основные вузы Москвы и области
    assert len(slugs) >= 20
    assert "fu" in slugs      # Финансовый университет
    assert "hse" in slugs     # ВШЭ
    assert "mifi" in slugs
    assert "rudn" in slugs
    # без повторов и все похожи на слаги
    assert len(slugs) == len(set(slugs))
    assert all(s.replace("_", "").replace("-", "").isalnum() for s in slugs)
