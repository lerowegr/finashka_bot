from app.scraper.parsers.program_card import parse_program_card


def test_ranepa_economics_card(load_fixture):
    card = parse_program_card(load_fixture("program_card_2.html"), 2)

    assert card.id == 2
    assert card.direction_code == "38.03.01"
    assert card.level == "bachelor"
    assert card.profile == "Экономика, финансы и анализ данных"
    assert card.faculty == "Институт экономики, математики и информационных технологий"

    assert card.exams.required == ["Русский язык", "Математика"]
    assert card.exams.choice == ["Обществознание", "ИКТ"]

    assert len(card.forms) == 1, "заочная и очно-заочная не представлены"
    full = card.forms[0]
    assert full.form == "full"
    assert full.pass_score == 270
    assert full.pass_score_year == 2025
    assert full.pass_score_delta == -10
    assert full.budget_seats == 50
    assert full.seats_main == 35
    assert full.seats_quota == 15
    assert full.avg_enrolled_score == 280
    assert full.tuition == 545000
    assert full.paid_only is False
