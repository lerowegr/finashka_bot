from app.scraper.parsers.sitemap import parse_sitemap


def test_sitemap_index(load_fixture):
    index = parse_sitemap(load_fixture("sitemap_head.xml"))
    assert "agatu" in index.vuz_slugs
    assert index.np_ids, "в фикстуре должны быть id направлений"
    assert index.program_ids, "в фикстуре должны быть id программ"
    assert all(isinstance(i, int) for i in index.np_ids + index.program_ids)
