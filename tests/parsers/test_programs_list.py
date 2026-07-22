from app.scraper.parsers.programs_list import parse_program_cards


def test_agatu_programs(load_fixture):
    programs = parse_program_cards(load_fixture("vuz_programs_agatu.html"))
    assert len(programs) == 15

    by_id = {p.id: p for p in programs}

    bio = by_id[10822]
    assert bio.name == "Биология"
    assert bio.direction_code == "06.03.01"
    assert bio.level == "bachelor"
    assert bio.profile == "Охотоведение"
    assert bio.faculty == "Факультет ветеринарной медицины"
    assert bio.exams.required == ["Русский язык", "Биология"]
    assert bio.exams.choice == ["Математика", "ИКТ", "Химия", "Физика"]
    assert len(bio.pass_scores) == 1
    assert bio.pass_scores[0].form == "full"
    assert bio.pass_scores[0].score == 99
    assert bio.pass_scores[0].year == 2025
    assert bio.paid_only is False

    # программа только с платным приёмом
    it = by_id[10823]
    assert it.direction_code == "09.03.02"
    assert it.paid_only is True
    assert it.pass_scores == []

    # заочная форма распознаётся
    food = next(p for p in programs if p.direction_code == "19.03.04")
    assert food.pass_scores[0].form == "extramural"
