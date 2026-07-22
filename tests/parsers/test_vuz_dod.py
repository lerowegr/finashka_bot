from datetime import date

from app.scraper.parsers.vuz_dod import parse_vuz_dod

REF = date(2026, 7, 22)  # дата, на которую сохранены фикстуры


def test_itmo_dod(load_fixture):
    events = parse_vuz_dod(load_fixture("vuz_dod_itmo.html"), today=REF)
    assert len(events) == 2

    first = events[0]
    assert first.starts_at.month == 7 and first.starts_at.day == 22
    assert "День открытых дверей" in first.title
    assert first.location and "Санкт-Петербург" in first.location

    # второе событие в августе — год выведен корректно
    assert events[1].starts_at.month == 8


def test_mifi_dod_uses_description_as_title(load_fixture):
    events = parse_vuz_dod(load_fixture("vuz_dod_mifi.html"), today=REF)
    assert len(events) == 1
    event = events[0]
    assert event.starts_at.hour == 10
    # название вуза как строку-шум отбрасываем, берём содержательное описание
    assert "Информацион" in event.title
    assert event.location and "Москва" in event.location


def test_no_dod_returns_empty(load_fixture):
    # у АГАТУ нет анонсов, а боковые блоки других вузов не должны просочиться
    assert parse_vuz_dod(load_fixture("vuz_dod_agatu.html"), today=REF) == []
