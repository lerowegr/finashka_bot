"""Юнит-тесты оценки шансов поступления (чистая логика, без БД)."""

from types import SimpleNamespace as NS

from app.domain.services import profile

# id предметов условные: 1=русский, 2=математика, 3=физика, 4=информатика


def _program(required, choice, pass_score, form="full"):
    exams = [NS(subject_id=s, kind="required") for s in required]
    exams += [NS(subject_id=s, kind="choice") for s in choice]
    forms = [NS(form=form, pass_score=pass_score, pass_score_year=2025)]
    return NS(exams=exams, forms=forms)


def test_no_scores_is_unknown():
    prog = _program([1, 2], [3, 4], 200)
    assert profile.evaluate(prog, {})[0] == "unknown"


def test_pass_with_margin():
    prog = _program([1, 2], [3, 4], 200)
    # 90 + 90 + max(80, 10) = 260 >= 200 + 10
    status, total, pass_score = profile.evaluate(prog, {1: 90, 2: 90, 3: 80, 4: 10})
    assert status == "pass"
    assert total == 260
    assert pass_score == 200


def test_edge_zone():
    prog = _program([1, 2], [], 200)
    # 100 + 98 = 198, в зоне [pass-5, pass+10)
    assert profile.evaluate(prog, {1: 100, 2: 98})[0] == "edge"


def test_low_when_short():
    prog = _program([1, 2], [], 200)
    # 80 + 80 = 160 < 200 - 5
    assert profile.evaluate(prog, {1: 80, 2: 80})[0] == "low"


def test_missing_required_subject():
    prog = _program([1, 2], [3], 200)
    # нет обязательной математики (id=2)
    assert profile.evaluate(prog, {1: 90, 3: 90})[0] == "missing"


def test_missing_when_no_choice_subject_available():
    prog = _program([1], [3, 4], 150)
    # есть обязательный, но ни одного предмета «на выбор»
    assert profile.evaluate(prog, {1: 95})[0] == "missing"


def test_unknown_when_no_pass_score():
    prog = _program([1, 2], [], pass_score=None)
    assert profile.evaluate(prog, {1: 90, 2: 90})[0] == "unknown"


def test_status_prefix():
    assert profile.status_prefix("pass") == "🟢 "
    assert profile.status_prefix("unknown") == ""
