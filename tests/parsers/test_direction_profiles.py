"""Страница /vuzu/{slug}/proxodnoi?{np_id} — все профили одного направления в вузе."""

from app.scraper.parsers.programs_list import parse_program_cards


def test_mpei_direction_profiles(load_fixture):
    # МЭИ, направление 01.03.02 (np_id 1002) — на сайте два профиля
    programs = parse_program_cards(load_fixture("vuz_direction_mpei_1002.html"))
    assert len(programs) == 2

    assert {p.direction_code for p in programs} == {"01.03.02"}
    profiles = {p.profile for p in programs}
    assert "Математическое моделирование" in profiles
    # у каждого профиля разобрались экзамены/баллы
    assert all(p.exams.required for p in programs)
