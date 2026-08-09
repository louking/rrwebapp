import pytest

from rrwebapp.raceresults import RaceResults, normalizeracetime, headerError, dataError

DISTANCE = 3.1  # 5k in miles

SIMPLE_CSV = (
    "Place,Name,Gender,Age,Time,City,State,Club\n"
    "1,Jane Doe,F,30,20:00,Frederick,MD,FSRC\n"
    "2,John Smith,M,35,22:30,Frederick,MD,FSRC\n"
)


def _write(tmp_path, text, name='results.csv'):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_normalizeracetime_converts_hhmmss_to_seconds():
    assert normalizeracetime('20:00', DISTANCE) == 1200.0


def test_raceresults_parses_rows(tmp_path, dbapp):
    filename = _write(tmp_path, SIMPLE_CSV)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)

        first = next(rr)
        second = next(rr)
        rr.close()

    assert first['place'] == 1
    assert first['name'] == 'Jane Doe'
    assert first['gender'] == 'F'
    assert first['age'] == 30
    assert first['city'] == 'Frederick'
    assert first['state'] == 'MD'
    assert first['club'] == 'FSRC'
    assert first['time'] == 1200.0

    assert second['place'] == 2
    assert second['time'] == 1350.0


def test_raceresults_raises_stopiteration_at_end(tmp_path, dbapp):
    filename = _write(tmp_path, SIMPLE_CSV)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)
        next(rr)
        next(rr)
        with pytest.raises(StopIteration):
            next(rr)
        rr.close()


def test_raceresults_splits_first_last_name_fields(tmp_path, dbapp):
    csv_text = (
        "Place,First,Last,Gender,Age,Time\n"
        "1,Jane,Doe,F,30,20:00\n"
    )
    filename = _write(tmp_path, csv_text)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)
        row = next(rr)
        rr.close()

    assert row['name'] == 'Jane Doe'
    assert 'firstname' not in row
    assert 'lastname' not in row


def test_raceresults_skips_rows_with_empty_time(tmp_path, dbapp):
    csv_text = (
        "Place,Name,Gender,Age,Time\n"
        "1,Jane Doe,F,30,\n"
        "2,John Smith,M,35,22:30\n"
    )
    filename = _write(tmp_path, csv_text)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)
        row = next(rr)
        rr.close()

    assert row['place'] == 2
    assert row['name'] == 'John Smith'


def test_raceresults_raises_dataerror_for_invalid_age(tmp_path, dbapp):
    csv_text = (
        "Place,Name,Gender,Age,Time\n"
        "1,Jane Doe,F,notanumber,20:00\n"
    )
    filename = _write(tmp_path, csv_text)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)
        with pytest.raises(dataError):
            next(rr)
        rr.close()


def test_raceresults_raises_dataerror_for_invalid_name(tmp_path, dbapp):
    csv_text = (
        "Place,Name,Gender,Age,Time\n"
        "1,-Invalid,F,30,20:00\n"
    )
    filename = _write(tmp_path, csv_text)
    with dbapp.app_context():
        rr = RaceResults(filename, DISTANCE)
        with pytest.raises(dataError):
            next(rr)
        rr.close()


def test_raceresults_raises_headererror_when_no_header_found(tmp_path, dbapp):
    csv_text = "not,a,valid,results,header\nfoo,bar,baz,qux,quux\n"
    filename = _write(tmp_path, csv_text)
    with dbapp.app_context():
        with pytest.raises(headerError):
            RaceResults(filename, DISTANCE)
