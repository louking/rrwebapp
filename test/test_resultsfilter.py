import csv
from datetime import time as datetime_time, timedelta

import pytest

from rrwebapp.model import db, Club, Race, Runner, Series
from rrwebapp.raceresults import RaceResults
from rrwebapp.resultsutils import ImportResults, Record
from rrwebapp.resultsfilter import (
    MAXAGE, ResultsFilter, findheader, headerError, parseagegroup, rendertime, renderplace,
)

RACEDATE = '2026-10-25'

# ages on RACEDATE: Jane 41, John 36, Mary 60
MEMBERS = [
    ('Jane Doe', '1985-01-01', 'F'),
    ('John Smith', '1990-03-03', 'M'),
    ('Mary Older', '1966-06-06', 'F'),
]

MCM_HEADER = 'Place,Bib,Name,Age Group,Gender,Gun Time,Chip Time,Race'


@pytest.mark.parametrize('value, expected', [
    ('35 to 39', (35, 39, None)),
    ('35-39', (35, 39, None)),
    ('M35-39', (35, 39, 'M')),
    ('F 40 - 44', (40, 44, 'F')),
    ('M4044', (40, 44, 'M')),
    ('80+', (80, MAXAGE, None)),
    ('80 & Over', (80, MAXAGE, None)),
    ('60 and up', (60, MAXAGE, None)),
    ('19 & Under', (0, 19, None)),
    ('Under 20', (0, 19, None)),
    ('42', (42, 42, None)),
    (42, (42, 42, None)),
    ('', (None, None, None)),
    (None, (None, None, None)),
    ('Open', (None, None, None)),
    ('Masters', (None, None, None)),
])
def test_parseagegroup(value, expected):
    assert parseagegroup(value) == expected


def test_findheader_mcm():
    cols = findheader(MCM_HEADER.split(','))
    assert cols == {'place': 0, 'name': 2, 'agegroup': 3, 'gender': 4, 'guntime': 5, 'chiptime': 6}


def test_findheader_split_names_and_age():
    cols = findheader(['Place', 'First Name', 'Last Name', 'Name', 'Age', 'Sex', 'Time'])
    assert 'name' not in cols
    assert cols['firstname'] == 1 and cols['lastname'] == 2 and cols['age'] == 4


def test_findheader_rejects_non_header():
    assert findheader(['1', '1', 'Kyle King', '35 to 39', 'M', '02:17:30']) is None
    # no age or age group
    assert findheader(['Place', 'Name', 'Gender', 'Time']) is None


def test_rendertime():
    assert rendertime(' 03:01:02.5 ') == '03:01:02.5'
    assert rendertime(datetime_time(3, 1, 2)) == '3:01:02.000'
    assert rendertime(timedelta(hours=3, minutes=1, seconds=2.5)) == '3:01:02.500'
    assert rendertime(0.125) == '3:00:00.000'   # excel days
    assert rendertime(None) == ''


def test_renderplace():
    assert renderplace('12') == '12'
    assert renderplace(12.0) == '12'
    assert renderplace('DNF') == ''


def _mkrace(membersonly=True):
    club = Club(shname='c', name='Club C')
    db.session.add(club)
    db.session.flush()
    series = Series(club_id=club.id, name='Grand Prix', year=2026, membersonly=membersonly)
    race = Race(club_id=club.id, name='Marathon', year=2026, date=RACEDATE, distance=26.2188, fixeddist='26.22')
    race.series.append(series)
    db.session.add_all([series, race])
    for name, dob, gender in MEMBERS:
        db.session.add(Runner(club.id, name=name, dateofbirth=dob, gender=gender))
    db.session.commit()
    return club, race


def _filter(tmp_path, lines, membersonly=True):
    infile = tmp_path / 'in.csv'
    infile.write_text('\n'.join(lines) + '\n', encoding='utf8')
    outfile = tmp_path / 'out.csv'
    club, race = _mkrace(membersonly)
    importer = ImportResults(club.id, race.id)
    rf = ResultsFilter(str(infile), importer)
    stats = rf.filter(str(outfile))
    rf.close()
    with open(outfile, newline='', encoding='utf8') as f:
        rows = list(csv.DictReader(f))
    return stats, rows, outfile, importer


def _importdisposition(importer, name, age):
    '''disposition Import gives a result with this name and age'''
    result = Record()
    result.name = name
    result.age = age
    result.runnerid = None
    importer.dbresult = result
    return importer.set_initialdisposition({})


MCM_LINES = [
    MCM_HEADER,
    '1,1,Somebody Else,35 to 39,M,02:17:30.803,02:17:29.569,Marathon',   # no similar name
    '2,2,Jane Doe,40 to 44,F,03:00:00.000,02:59:00.000,Marathon',        # in range
    '3,3,Jon Smith,30 to 34,M,03:10:00.000,03:09:00.000,Marathon',       # similar name, 36 is near 30-34
    '4,4,John Smith,20 to 24,M,03:20:00.000,03:19:00.000,Marathon',      # too far from 36
    '6,6,Mary Older,,F,04:00:00.000,03:59:00.000,Marathon',              # no age group
    '7,7,Jane Doe,40 to 44,F,,,Marathon',                                # no time (DNF)
    '10,10,John Smith Jr.,35 to 39,M,04:30:00.000,04:29:00.000,Marathon',  # similar name, in range
]


def test_filter_age_groups(dbapp, tmp_path):
    stats, rows, _, importer = _filter(tmp_path, MCM_LINES)

    assert stats == {'read': 6, 'kept': 4, 'agefrommember': 1}
    byplace = {r['place']: r for r in rows}
    assert set(byplace) == {'2', '3', '6', '10'}

    assert byplace['2']['age'] == '41'
    # both times are written, under names Import recognizes
    assert byplace['2']['chiptime'] == '02:59:00.000'
    assert byplace['2']['guntime'] == '03:00:00.000'
    assert 'time' not in byplace['2']
    assert byplace['2']['age group'] == '40 to 44'
    assert byplace['2']['filter note'] == 'definite'

    # member's age clamped to the nearest bound of the age group
    assert byplace['3']['age'] == '34'
    assert byplace['3']['filter note'] == 'closeage'

    # no age group, age from member record
    assert byplace['6']['age'] == '60'
    assert byplace['6']['filter note'] == 'definite; age from member record, no age group in file'

    assert byplace['10']['age'] == '36'
    assert byplace['10']['filter note'] == 'similar'

    # every kept row gets the same disposition from Import
    for r in rows:
        assert r['filter note'].split(';')[0] == _importdisposition(importer, r['name'], int(r['age']))


def test_filter_real_age(dbapp, tmp_path):
    lines = [
        'Place,Name,Age,Gender,Time',
        '1,Somebody Else,30,M,1:00:00',
        '2,Jane Doe,41,F,1:01:00',      # exact name and age
        '3,John Smith,38,M,1:02:00',    # member is 36, within AGE_DELTAMAX
        '4,Jon Smith,36,M,1:03:00',     # similar name, same age
        '5,John Smith,45,M,1:04:00',    # too far from 36
    ]
    stats, rows, _, importer = _filter(tmp_path, lines)
    assert stats == {'read': 5, 'kept': 3, 'agefrommember': 0}
    byplace = {r['place']: r for r in rows}
    assert set(byplace) == {'2', '3', '4'}
    # the file's age is written unchanged
    assert [byplace[p]['age'] for p in '234'] == ['41', '38', '36']
    assert [byplace[p]['filter note'] for p in '234'] == ['definite', 'closeage', 'similar']
    assert byplace['2']['time'] == '1:01:00'


def test_filter_not_membersonly_keeps_missed(dbapp, tmp_path):
    # Edit Participants shows unmatched results as missed when the series isn't members only
    stats, rows, _, _ = _filter(tmp_path, MCM_LINES, membersonly=False)
    assert stats['kept'] == stats['read'] == 6
    byplace = {r['place']: r for r in rows}
    assert byplace['1']['filter note'] == 'missed'
    assert byplace['2']['filter note'] == 'definite'


def test_filter_output_imports(dbapp, tmp_path):
    lines = [
        'Place,First Name,Last Name,Division,Chip Time,City,State',
        '10,Jane,Doe,F4044,1:02:03,Frederick,MD',
        '11,John,Smith,M35-39,1:05:00,Walkersville,MD',
    ]
    stats, rows, outfile, _ = _filter(tmp_path, lines)
    assert stats['kept'] == 2
    # gender comes from the division prefix when there's no gender column
    assert [r['gender'] for r in rows] == ['F', 'M']

    rr = RaceResults(str(outfile), 6.2137)
    results = [next(rr), next(rr)]
    with pytest.raises(StopIteration):
        next(rr)
    rr.close()

    assert results[0]['name'] == 'Jane Doe'
    assert results[0]['age'] == 41
    assert results[0]['place'] == 10
    assert results[0]['time'] == 3723
    assert results[1]['city'] == 'Walkersville'


def test_filter_no_header(app, tmp_path):
    infile = tmp_path / 'in.csv'
    infile.write_text('Place,Name,Gender,Time\n1,Jane Doe,F,1:00:00\n', encoding='utf8')
    with app.app_context():
        with pytest.raises(headerError):
            ResultsFilter(str(infile))


def test_filter_output_import_uses_chip_time(dbapp, tmp_path):
    lines = [
        MCM_HEADER,
        '2,2,Jane Doe,40 to 44,F,03:00:00.000,02:59:00.000,Marathon',
    ]
    _, rows, outfile, _ = _filter(tmp_path, lines)
    rr = RaceResults(str(outfile), 26.2188)
    result = next(rr)
    rr.close()
    assert result['time'] == 2 * 3600 + 59 * 60
