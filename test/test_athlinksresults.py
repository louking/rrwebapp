import datetime
from unittest.mock import MagicMock

from loutilities import timeu

from rrwebapp.athlinksresults import AthlinksCollect

ftime = timeu.asctime('%Y-%m-%d')

DOB = datetime.datetime(1990, 1, 1)  # 30 as of 2020-06-01
RACEDATE_EPOCHMS = str(int(ftime.asc2epoch('2020-06-01') * 1000))
BEGIN = ftime.asc2epoch('2020-01-01')
END = ftime.asc2epoch('2020-12-31')


def _result(age=30, gender='F', racedate=RACEDATE_EPOCHMS):
    return {
        'Race': {'RaceDate': racedate},
        'Gender': gender,
        'Age': age,
    }


def _collector(results):
    collect = AthlinksCollect()
    collect.service = MagicMock()
    collect.service.listathleteresults.return_value = results
    return collect


def test_getresults_includes_exact_age_and_gender_match():
    collect = _collector([_result(age=30, gender='F')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert len(results) == 1
    assert results[0]['fuzzyage'] is False


def test_getresults_excludes_gender_mismatch():
    collect = _collector([_result(age=30, gender='M')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_excludes_result_outside_date_window():
    outside = str(int(ftime.asc2epoch('2019-01-01') * 1000))
    collect = _collector([_result(age=30, gender='F', racedate=outside)])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_excludes_age_mismatch():
    '''
    documents current (buggy) behavior: the age-group "fuzzy match" branch relies on
    `(x/5)*5 != x`-style checks that were written for Python 2 integer division. Under
    Python 3 true division, `(n/5)*5` reconstructs `n` exactly for any int, so the intended
    "is this an age-group value" check never rejects anything, and the "does the runner's
    age fall in that group" check never matches (it recomputes racedateage, not resultage).
    Net effect: any age mismatch is skipped outright, fuzzy-age matching never fires.
    '''
    collect = _collector([_result(age=32, gender='F')])  # dob-implied age is 30
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []
