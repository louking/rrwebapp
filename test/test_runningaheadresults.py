import datetime
from unittest.mock import MagicMock

from loutilities import timeu

from rrwebapp.runningaheadresults import RunningAHEADCollect

ftime = timeu.asctime('%Y-%m-%d')

DOB = datetime.datetime(1990, 1, 1)  # 30 as of 2020-06-01
BEGIN = ftime.asc2epoch('2020-01-01')
END = ftime.asc2epoch('2020-12-31')

USER = {'token': 'tok1'}
RAUSER = {'givenName': 'Jane', 'familyName': 'Doe', 'birthDate': '1990-01-01'}


def _race_workout(duration=1200, distvalue=3.1, distunit='mi', date='2020-06-01', name='Frederick 5k'):
    return {
        'workoutName': 'Race',
        'details': {'duration': duration, 'distance': {'unit': distunit, 'value': distvalue}},
        'date': date,
        'course': {'name': name},
    }


def _collector(rausers, workouts):
    collect = RunningAHEADCollect()
    collect.rausers = rausers
    collect.service = MagicMock()
    collect.service.listworkouts.return_value = workouts
    return collect


def test_getresults_returns_empty_when_member_not_found(dbapp):
    with dbapp.app_context():
        collect = _collector([(USER, RAUSER)], [])
        results = collect.getresults('Nobody Else', 'Nobody', 'Else', 'F', DOB, BEGIN, END)

    assert results == []
    collect.service.listworkouts.assert_not_called()


def test_getresults_returns_race_workout_for_matched_member(dbapp):
    with dbapp.app_context():
        collect = _collector([(USER, RAUSER)], [_race_workout()])
        results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert len(results) == 1
    assert results[0]['race'] == 'Frederick 5k'
    assert results[0]['age'] == 30
    assert results[0]['GivenName'] == 'Jane'
    assert results[0]['FamilyName'] == 'Doe'


def test_getresults_skips_non_race_workouts(dbapp):
    with dbapp.app_context():
        workout = _race_workout()
        workout['workoutName'] = 'Training Run'
        collect = _collector([(USER, RAUSER)], [workout])
        results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_skips_workouts_missing_duration_detail(dbapp):
    with dbapp.app_context():
        workout = _race_workout()
        del workout['details']['duration']
        collect = _collector([(USER, RAUSER)], [workout])
        results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


def test_getresults_skips_zero_duration_workouts(dbapp):
    with dbapp.app_context():
        collect = _collector([(USER, RAUSER)], [_race_workout(duration=0)])
        results = collect.getresults('Jane Doe', 'Jane', 'Doe', 'F', DOB, BEGIN, END)

    assert results == []


# ---------------------------------------------------------------------------
# convertserviceresult -- only the DB-independent early-return path
# ---------------------------------------------------------------------------

def test_convertserviceresult_skips_when_distance_too_short(dbapp):
    with dbapp.app_context():
        collect = _collector([], [])
        collect.club_id = 1
        collect.name, collect.fname, collect.lname = 'Jane Doe', 'Jane', 'Doe'
        collect.gender, collect.dob, collect.dt_dob = 'F', '1990-01-01', DOB

        result = {'race': 'Frederick Fun Run', 'date': '2020-06-01', 'miles': 0.01, 'km': 0.01, 'time': '5:00'}
        outrec = collect.convertserviceresult(result)

    assert outrec is None
