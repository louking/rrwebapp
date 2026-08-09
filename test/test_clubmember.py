import io

from rrwebapp.clubmember import CsvClubMember, getratio

SIMPLE_CSV = (
    "First,Last,DOB,Gender,City,State\n"
    "Jane,Doe,1990-01-01,F,Frederick,MD\n"
    "John,Smith,1985-05-05,M,Frederick,MD\n"
)


def _mkclubmember(csv_text=SIMPLE_CSV, **kwargs):
    return CsvClubMember(io.StringIO(csv_text), **kwargs)


def test_getratio_identical_strings_is_1():
    assert getratio('Jane Doe', 'Jane Doe') == 1.0


def test_getratio_completely_different_strings_is_low():
    assert getratio('Jane Doe', 'zzz') < 0.3


def test_csvclubmember_parses_rows(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        members = cm.getmembers()

    assert 'jane doe' in members
    assert members['jane doe'][0]['dob'] == '1990-01-01'
    assert members['jane doe'][0]['gender'] == 'F'
    assert members['jane doe'][0]['hometown'] == 'Frederick, MD'


def test_getmember_exact_match(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        result = cm.getmember('Jane Doe')

    assert result['exactmatch'] is True
    assert result['matchingmembers'][0]['name'] == 'Jane Doe'
    assert result['closematches'] == []


def test_getmember_no_match_returns_empty_dict(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        result = cm.getmember('Nobody Atall')

    assert result == {}


def test_getmember_close_match_not_exact(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember(cutoff=0.6)
        result = cm.getmember('Jane Doi')  # close typo

    assert result['exactmatch'] is False
    assert result['matchingmembers'][0]['name'] == 'Jane Doe'


def test_findmember_matches_on_name_and_age(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        # Jane Doe dob 1990-01-01, so age as of 2020-06-01 is 30
        found = cm.findmember('Jane Doe', 30, '2020-06-01')

    assert found == ('Jane Doe', '1990-01-01')


def test_findmember_returns_none_when_name_not_found(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        assert cm.findmember('Nobody Atall', 30, '2020-06-01') is None


def test_findmember_age_mismatch_goes_to_missedmatches(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        # correct name, wrong age -- no exact age match, so ends up in missedmatches
        found = cm.findmember('Jane Doe', 99, '2020-06-01')
        missed = cm.getmissedmatches()

    assert found is None
    assert len(missed) == 1
    assert missed[0]['dbname'] == 'Jane Doe'


def test_findname_finds_regardless_of_age(dbapp):
    with dbapp.app_context():
        cm = _mkclubmember()
        assert cm.findname('Jane Doe') == 'Jane Doe'
        assert cm.findname('Nobody Atall') is None


def test_clubmember_stops_at_first_blank_name_row(dbapp):
    csv_text = (
        "First,Last,DOB,Gender,City,State\n"
        "Jane,Doe,1990-01-01,F,Frederick,MD\n"
        ",,,,,\n"
        "John,Smith,1985-05-05,M,Frederick,MD\n"
    )
    with dbapp.app_context():
        cm = _mkclubmember(csv_text)
        members = cm.getmembers()

    assert 'jane doe' in members
    assert 'john smith' not in members
