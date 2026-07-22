from app.scraper.parsers.vuz_about import parse_vuz_about


def test_agatu_about(load_fixture):
    vuz = parse_vuz_about(load_fixture("vuz_about_agatu.html"), "agatu")

    assert vuz.short_name == "АГАТУ"
    assert "Арктический государственный" in vuz.full_name
    assert vuz.region_name == "Республика Саха (Якутия)"
    assert vuz.region_slug == "sahayakutia"
    assert vuz.is_state is True
    assert vuz.is_branch is False
    assert vuz.category == "C"

    assert vuz.directions_count == 14
    assert vuz.programs_count == 15
    assert vuz.budget_seats == 403
    assert vuz.avg_score == 42.5

    assert len(vuz.directions) == 14
    first = vuz.directions[0]
    assert first.code == "06.03.01"
    assert first.level == "bachelor"
    assert first.name == "Биология"
    assert first.np_id > 0

    # специалитет тоже распознан
    assert any(d.level == "specialist" for d in vuz.directions)

    assert len(vuz.faculties) == 5
    assert "Инженерный факультет" in vuz.faculties
    assert vuz.ugsn_names.get("06.00.00") == "БИОЛОГИЧЕСКИЕ НАУКИ"


def test_hse_about_smoke(load_fixture):
    """Второй вуз другой структуры — парсер не должен зависеть от частностей АГАТУ."""
    vuz = parse_vuz_about(load_fixture("vuz_about_hse.html"), "hse")
    assert vuz.short_name
    assert vuz.full_name
    assert vuz.directions, "у ВШЭ должен быть список направлений"
    assert vuz.region_name
    assert all(d.code.count(".") == 2 for d in vuz.directions)
