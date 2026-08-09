import datetime
from unittest.mock import MagicMock

from loutilities import timeu

from rrwebapp.ultrasignupresults import UltraSignupCollect

ftime = timeu.asctime('%Y-%m-%d')

DOB = datetime.datetime(1990, 1, 1)  # 30 as of 2020-06-01
BEGIN = ftime.asc2epoch('2020-01-01')
END = ftime.asc2epoch('2020-12-31')


def _result(age=30, gender='F', racedate='2020-06-01'):
    result = MagicMock()
    result.age = age
    result.gender = gender
    result.racedate = racedate
    return result


def _collector(results):
    collect = UltraSignupCollect()
    collect.service = MagicMock()
    collect.service.listresults.return_value = results
    return collect


def test_getresults_includes_exact_age_and_gender_match():
    collect = _collector([_result(age=30, gender='F')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == [collect.service.listresults.return_value[0]]


def test_getresults_excludes_age_mismatch():
    collect = _collector([_result(age=31, gender='F')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_excludes_gender_mismatch():
    collect = _collector([_result(age=30, gender='M')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_excludes_result_outside_date_window():
    collect = _collector([_result(age=30, gender='F', racedate='2019-01-01')])
    results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_convertserviceresult_skips_timed_hour_events(dbapp):
    with dbapp.app_context():
        collect = _collector([])
        collect.club_id = 1
        collect.name, collect.fname, collect.lname = 'Jane Doe', 'Jane', 'Doe'
        collect.gender, collect.dob, collect.dt_dob = 'F', '1990-01-01', DOB

        result = _result(age=30, gender='F', racedate='2020-06-01')
        result.racename = '6 hrs'
        outrec = collect.convertserviceresult(result)

    assert outrec is None


def test_convertserviceresult_skips_dnf_int_time(dbapp):
    with dbapp.app_context():
        collect = _collector([])
        collect.club_id = 1
        collect.name, collect.fname, collect.lname = 'Jane Doe', 'Jane', 'Doe'
        collect.gender, collect.dob, collect.dt_dob = 'F', '1990-01-01', DOB

        result = _result(age=30, gender='F', racedate='2020-06-01')
        result.racename = 'Frederick Ultra'
        result.distmiles = 50.0
        result.distkm = 80.5
        result.racetime = 0  # int => DNF sentinel

        outrec = collect.convertserviceresult(result)

    assert outrec is None
