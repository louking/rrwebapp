import pytest
from sqlalchemy.exc import IntegrityError

from rrwebapp.model import (
    db, getunique, update, insert_or_update, dbConsistencyError, parameterError,
    Club, Runner, Race, RaceResult, Series, ApiCredentials,
)


# ---------------------------------------------------------------------------
# getunique / update / insert_or_update
# ---------------------------------------------------------------------------

def test_getunique_returns_none_when_no_match(dbapp):
    with dbapp.app_context():
        assert getunique(db.session, ApiCredentials, name='nonesuch') is None


def test_getunique_returns_single_match(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='athlinks', key='k'))
        db.session.commit()

        found = getunique(db.session, ApiCredentials, name='athlinks')

    assert found.key == 'k'


def test_getunique_raises_on_multiple_matches(dbapp):
    with dbapp.app_context():
        db.session.add(Club(shname='a', name='Club A'))
        db.session.add(Club(shname='b', name='Club B'))
        db.session.commit()

        with pytest.raises(dbConsistencyError):
            # location is None for both, so this query matches both rows
            getunique(db.session, Club, location=None)


def test_update_returns_false_when_nothing_changed(dbapp):
    with dbapp.app_context():
        old = ApiCredentials(name='athlinks', key='k', secret='s')
        db.session.add(old)
        db.session.commit()

        same = ApiCredentials(name='athlinks', key='k', secret='s')
        updated = update(db.session, ApiCredentials, old, same, skipcolumns=['id'])

    assert updated is False


def test_update_applies_changed_columns_and_skips_skipcolumns(dbapp):
    with dbapp.app_context():
        old = ApiCredentials(name='athlinks', key='k', secret='s')
        db.session.add(old)
        db.session.commit()
        oldid = old.id

        changed = ApiCredentials(name='athlinks', key='newkey', secret='s')
        updated = update(db.session, ApiCredentials, old, changed, skipcolumns=['id'])

    assert updated is True
    assert old.key == 'newkey'
    assert old.id == oldid  # id was in skipcolumns, so untouched


def test_insert_or_update_inserts_new_row(dbapp):
    with dbapp.app_context():
        newrow = ApiCredentials(name='athlinks', key='k')
        updated = insert_or_update(db.session, ApiCredentials, newrow, skipcolumns=['id'], name='athlinks')

        assert updated is True
        assert ApiCredentials.query.filter_by(name='athlinks').one().key == 'k'


def test_insert_or_update_updates_existing_row(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='athlinks', key='k'))
        db.session.commit()

        changed = ApiCredentials(name='athlinks', key='newkey')
        updated = insert_or_update(db.session, ApiCredentials, changed, skipcolumns=['id'], name='athlinks')

        assert updated is True
        # only one row exists -- the original was updated in place, not duplicated
        assert ApiCredentials.query.filter_by(name='athlinks').count() == 1
        assert ApiCredentials.query.filter_by(name='athlinks').one().key == 'newkey'


# ---------------------------------------------------------------------------
# Runner date validation
# ---------------------------------------------------------------------------

def test_runner_accepts_valid_dateofbirth(dbapp):
    with dbapp.app_context():
        runner = Runner(club_id=1, name='Jane Doe', dateofbirth='1990-01-01')
        assert runner.dateofbirth == '1990-01-01'


def test_runner_defaults_missing_dateofbirth_to_empty_string(dbapp):
    with dbapp.app_context():
        runner = Runner(club_id=1, name='Jane Doe')
        assert runner.dateofbirth == ''


def test_runner_rejects_invalid_dateofbirth(dbapp):
    with dbapp.app_context():
        with pytest.raises(parameterError):
            Runner(club_id=1, name='Jane Doe', dateofbirth='not-a-date')


def test_runner_rejects_invalid_renewdate(dbapp):
    with dbapp.app_context():
        with pytest.raises(parameterError):
            Runner(club_id=1, name='Jane Doe', renewdate='not-a-date')


# ---------------------------------------------------------------------------
# Series.has_series_option
# ---------------------------------------------------------------------------

def test_has_series_option_boolean_column(dbapp):
    with dbapp.app_context():
        series = Series(membersonly=True)
        assert series.has_series_option('membersonly') is True

        series.membersonly = False
        assert series.has_series_option('membersonly') is False


def test_has_series_option_text_list_when_set(dbapp):
    with dbapp.app_context():
        series = Series(options='proportional_scoring, requires_club_affiliation')
        assert series.has_series_option('proportional_scoring') is True
        assert series.has_series_option('display_club_affiliation') is False


def test_has_series_option_text_list_when_unset(dbapp):
    with dbapp.app_context():
        series = Series(options=None)
        assert series.has_series_option('proportional_scoring') is False


# ---------------------------------------------------------------------------
# unique constraints
# ---------------------------------------------------------------------------

def test_race_unique_constraint_rejects_duplicate(dbapp):
    with dbapp.app_context():
        db.session.add(Club(shname='c', name='Club C'))
        db.session.commit()
        club = Club.query.first()

        db.session.add(Race(club_id=club.id, name='Turkey Trot', year=2025, date='2025-11-27', fixeddist='5'))
        db.session.commit()

        db.session.add(Race(club_id=club.id, name='Turkey Trot', year=2025, date='2025-11-27', fixeddist='5'))
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_raceresult_unique_constraint_does_not_prevent_null_runnername_duplicates(dbapp):
    '''
    documents a known gotcha: RaceResult's UniqueConstraint includes runnername, but the
    tabulate flow never sets it, so it's always NULL -- and SQL treats NULL != NULL, so
    the constraint does not actually block duplicate rows in that case
    '''
    with dbapp.app_context():
        db.session.add(Club(shname='c', name='Club C'))
        db.session.commit()
        club = Club.query.first()

        result1 = RaceResult(club.id, 1, 1, 1, 1200.0, 'M', 30)
        result2 = RaceResult(club.id, 1, 1, 1, 1200.0, 'M', 30)
        db.session.add(result1)
        db.session.add(result2)
        # does not raise, even though every other column matches
        db.session.commit()

        assert RaceResult.query.filter_by(club_id=club.id).count() == 2
