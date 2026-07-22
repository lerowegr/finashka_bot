from app.scraper.parsers.vuz_obsh import parse_vuz_obsh


def test_agatu_obsh(load_fixture):
    info = parse_vuz_obsh(load_fixture("vuz_obsh_agatu.html"))
    assert info.dorm == "not_all"
    assert info.dorm_rating == 1.95
