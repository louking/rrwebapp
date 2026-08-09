import datetime
from unittest.mock import patch, MagicMock

from rrwebapp.model import (
    db, Club, Runner, Race, ManagedResult, Exclusion,
    ApiCredentials, RaceResultService, ClubAffiliation, Location,
)
from rrwebapp.resultsutils import (
    race_fixeddist, get_distance, normname, filtermissed, get_earliestrace,
    ServiceAttributes, ClubAffiliationLookup, clubaffiliationelement, LocationServer,
    ServiceResultFile,
)


# ---------------------------------------------------------------------------
# pure functions
# ---------------------------------------------------------------------------

def test_race_fixeddist_formats_to_4_significant_digits():
    assert race_fixeddist(3.1) == '3.1'
    assert race_fixeddist(26.21875) == '26.22'
    assert race_fixeddist(5) == '5'


def test_normname_capitalizes_name():
    assert normname('john smith') == 'John Smith'
    assert normname('MARY JONES') == 'Mary Jones'


def test_get_distance_returns_none_when_either_location_errored():
    loc1 = Location(name='a', latitude=1.0, longitude=1.0, lookuperror=True)
    loc2 = Location(name='b', latitude=2.0, longitude=2.0, lookuperror=False)
    assert get_distance(loc1, loc2) is None

    loc1.lookuperror = False
    loc2.lookuperror = True
    assert get_distance(loc1, loc2) is None


def test_get_distance_computes_great_circle_distance():
    # Boston City Hall to NYC City Hall, roughly 190 miles
    loc1 = Location(name='boston', latitude=42.3601, longitude=-71.0589, lookuperror=False)
    loc2 = Location(name='nyc', latitude=40.7128, longitude=-74.0060, lookuperror=False)
    dist = get_distance(loc1, loc2)
    assert 180 < dist < 200


# ---------------------------------------------------------------------------
# filtermissed / get_earliestrace (dbapp)
# ---------------------------------------------------------------------------

def _mkclub():
    club = Club(shname='c', name='Club C')
    db.session.add(club)
    db.session.commit()
    return club


def test_filtermissed_returns_empty_list_when_no_resultage(dbapp):
    with dbapp.app_context():
        assert filtermissed(1, [{'dob': '2000-01-01'}], '2020-01-01', None) == []
        assert filtermissed(1, [{'dob': '2000-01-01'}], '2020-01-01', 0) == []


def test_filtermissed_excludes_entries_outside_age_delta(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        # runner is ~50 as of 2020-01-01 (dob 1970-01-01), way outside AGE_DELTAMAX=3 of resultage=30
        db.session.add(Runner(club.id, name='Jane Doe', dateofbirth='1970-01-01'))
        db.session.commit()
        runner = Runner.query.filter_by(club_id=club.id).one()

        missed = [{'name': 'Jane D', 'dbname': 'Jane Doe', 'dob': '1970-01-01'}]
        result = filtermissed(club.id, missed, '2020-01-01', 30)

    assert result == []


def test_filtermissed_keeps_entries_within_age_delta_and_not_excluded(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        # runner is 30 as of 2020-01-01
        db.session.add(Runner(club.id, name='Jane Doe', dateofbirth='1990-01-01'))
        db.session.commit()
        runner = Runner.query.filter_by(club_id=club.id).one()

        missed = [{'name': 'Jane D', 'dbname': 'Jane Doe', 'dob': '1990-01-01'}]
        result = filtermissed(club.id, missed, '2020-01-01', 30)

    assert result == missed


def test_filtermissed_excludes_entries_in_exclusions_table(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        db.session.add(Runner(club.id, name='Jane Doe', dateofbirth='1990-01-01'))
        db.session.commit()
        runner = Runner.query.filter_by(club_id=club.id).one()

        db.session.add(Exclusion(club_id=club.id, foundname='Jane D', runnerid=runner.id))
        db.session.commit()

        missed = [{'name': 'Jane D', 'dbname': 'Jane Doe', 'dob': '1990-01-01'}]
        result = filtermissed(club.id, missed, '2020-01-01', 30)

    assert result == []


def test_get_earliestrace_returns_earliest_within_year(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        runner = Runner(club.id, name='Jane Doe', dateofbirth='1990-01-01')
        db.session.add(runner)
        db.session.commit()

        early = Race(club_id=club.id, name='Spring 5k', year=2020, date='2020-03-01', fixeddist='3.1')
        late = Race(club_id=club.id, name='Fall 5k', year=2020, date='2020-10-01', fixeddist='3.1')
        other_year = Race(club_id=club.id, name='Winter 5k', year=2019, date='2019-01-01', fixeddist='3.1')
        db.session.add_all([early, late, other_year])
        db.session.commit()

        db.session.add(ManagedResult(club.id, late.id, name='Jane Doe', runnerid=runner.id))
        db.session.add(ManagedResult(club.id, early.id, name='Jane Doe', runnerid=runner.id))
        db.session.add(ManagedResult(club.id, other_year.id, name='Jane Doe', runnerid=runner.id))
        db.session.commit()

        result = get_earliestrace(runner, year=2020)

    assert result.raceid == early.id


def test_get_earliestrace_returns_none_when_no_results(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        runner = Runner(club.id, name='Jane Doe', dateofbirth='1990-01-01')
        db.session.add(runner)
        db.session.commit()

        assert get_earliestrace(runner, year=2020) is None


# ---------------------------------------------------------------------------
# ServiceAttributes
# ---------------------------------------------------------------------------

def test_serviceattributes_defaults_when_service_unconfigured(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        attrs = ServiceAttributes(club.id, 'athlinks')

    assert attrs.maxdistance is None


def test_serviceattributes_reads_configured_attrs(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        creds = ApiCredentials(name='athlinks', key='k')
        db.session.add(creds)
        db.session.commit()
        db.session.add(RaceResultService(club_id=club.id, apicredentials_id=creds.id, attrs='{"maxdistance": 26.2}'))
        db.session.commit()

        attrs = ServiceAttributes(club.id, 'athlinks')

    assert attrs.maxdistance == 26.2


# NOTE: ServiceAttributes.set_attr() is not covered here -- it queries RaceResultService
# by a 'name' kwarg that model doesn't have, and references self.service, which __init__
# never sets. Nothing in the codebase currently calls it; looks like dead/broken code.


# ---------------------------------------------------------------------------
# ClubAffiliationLookup / clubaffiliationelement
# ---------------------------------------------------------------------------

def test_clubaffiliationlookup_matches_known_alternates(dbapp):
    with dbapp.app_context():
        club = _mkclub()
        db.session.add(ClubAffiliation(club_id=club.id, year=2020, shortname='FSRC',
                                        title='Frederick Steeplechasers', alternates='fsrc||steeplechasers'))
        db.session.commit()

        lookup = ClubAffiliationLookup(club.id, 2020)

    assert lookup.knownclub('FSRC') is True
    assert lookup.knownclub('Steeplechasers') is True
    assert lookup.knownclub('unknown club') is False
    assert lookup.clubaffiliation('fsrc').shortname == 'FSRC'
    assert lookup.clubaffiliation('unknown club') is None


def test_clubaffiliationelement_returns_none_without_affiliation():
    result = MagicMock()
    result.clubaffiliation = None
    assert clubaffiliationelement(result) is None


def test_clubaffiliationelement_returns_span_with_affiliation():
    result = MagicMock()
    result.clubaffiliation.shortname = 'FSRC'
    result.clubaffiliation.title = 'Frederick Steeplechasers'
    element = clubaffiliationelement(result)
    assert 'FSRC' in element.render()


# ---------------------------------------------------------------------------
# LocationServer (mocked googlemaps)
# ---------------------------------------------------------------------------

def test_locationserver_getlocation_caches_new_location(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='googlemaps', key='fakekey'))
        db.session.commit()

        with patch('rrwebapp.resultsutils.Client') as MockClient, \
             patch('rrwebapp.resultsutils.geocode') as mock_geocode:
            mock_geocode.return_value = [{'geometry': {'location': {'lat': 39.4, 'lng': -77.4}}}]

            server = LocationServer()
            loc = server.getlocation('Frederick, MD')

    assert loc.latitude == 39.4
    assert loc.longitude == -77.4
    assert loc.lookuperror is False


def test_locationserver_getlocation_flags_lookuperror_when_no_results(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='googlemaps', key='fakekey'))
        db.session.commit()

        with patch('rrwebapp.resultsutils.Client'), \
             patch('rrwebapp.resultsutils.geocode') as mock_geocode:
            mock_geocode.return_value = []

            server = LocationServer()
            loc = server.getlocation('Nowhere, ZZ')

    assert loc.lookuperror is True


def test_locationserver_getlocation_uses_cached_row_without_calling_geocode(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='googlemaps', key='fakekey'))
        db.session.add(Location(name='Frederick, MD', latitude=39.4, longitude=-77.4,
                                 cached_at=datetime.datetime.now(), lookuperror=False))
        db.session.commit()

        with patch('rrwebapp.resultsutils.Client'), \
             patch('rrwebapp.resultsutils.geocode') as mock_geocode:
            server = LocationServer()
            loc = server.getlocation('Frederick, MD')

        mock_geocode.assert_not_called()

    assert loc.latitude == 39.4


# ---------------------------------------------------------------------------
# ServiceResultFile (plain file I/O, no db needed)
# ---------------------------------------------------------------------------

def test_serviceresultfile_reads_and_transforms_rows(tmp_path):
    csvfile = tmp_path / 'results.csv'
    csvfile.write_text('SourceName,SourceAge\nJane Doe,30\nJohn Doe,40\n')

    srf = ServiceResultFile('testservice', {'name': 'SourceName', 'age': 'SourceAge'})
    srf.open(str(csvfile))

    assert srf.count() == 2

    first = next(srf)
    assert first.name == 'Jane Doe'
    assert first.age == 30  # str2num converts numeric strings during transform

    second = next(srf)
    assert second.name == 'John Doe'

    assert next(srf) is None

    srf.close()
    assert not hasattr(srf, '_fh')
