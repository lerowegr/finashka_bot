from app.scraper.parsers.np_page import parse_np_page


def test_np_mathematics(load_fixture):
    np = parse_np_page(load_fixture("np_1001.html"), 1001)

    assert np.min_score == 39.67
    assert np.avg_score == 59.8
    assert len(np.programs) == 35, "сервер отдаёт первые 35 программ направления"

    rudn = np.programs[0]
    assert rudn.id == 1820
    assert rudn.direction_code == "01.03.01"
    assert rudn.name == "Математика"
    assert rudn.pass_scores[0].score == 217
