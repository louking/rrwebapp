#!/usr/bin/python
###########################################################################################
# racedb  -- manage race database
#
#	Date		Author		Reason
#	----		------		------
#       01/23/13        Lou King        Create
#       04/26/13        Lou King        temp fix for issue #20 - allow mysql+gaerdbms
#
#   Copyright 2013,2014 Lou King.  All rights reserved
#
###########################################################################################
'''
racedb  -- manage race database
===================================================

racedb has the following tables.  See classes of same name (with camelcase) for definitions.

    * runner
    * race
    * raceresult
    * raceseries
    * series
    * divisions
       
'''

# standard
import pdb
import argparse
import time

# pypi
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, types, cast, case
from sqlalchemy.types import TypeDecorator

# github

# other
from database_flask import *
from flask import session

# home grown
import version
from loutilities import timeu
import loutilities.renderrun as render

DBDATEFMT = '%Y-%m-%d'
t = timeu.asctime(DBDATEFMT)
dbdate = timeu.asctime(DBDATEFMT)

class dbConsistencyError(Exception): pass
class parameterError(Exception): pass

rolenames = ['admin','viewer']

MAX_RACENAME_LEN = 50
MAX_LOCATION_LEN = 64

getclubid = lambda form: session['club_id']
getyear   = lambda form: session['year']

#----------------------------------------------------------------------
def getunique(session, model, **kwargs):
#----------------------------------------------------------------------
    '''
    retrieve a row from the database, raising exception of more than one row exists for query criteria
    
    :param session: session within which update occurs
    :param model: table model
    :param kwargs: query criteria
    
    :rtype: single instance of the row, or None
    '''

    instances = session.query(model).filter_by(**kwargs).all()

    # error if query returned multiple rows when it was supposed to be unique
    if len(instances) > 1:
        raise dbConsistencyError, 'found multiple rows in {0} for {1}'.format(model,kwargs)
    
    if len(instances) == 0:
        return None
    
    return instances[0]

#----------------------------------------------------------------------
def update(session, model, oldinstance, newinstance, skipcolumns=[]):
#----------------------------------------------------------------------
    '''
    update an existing element based on kwargs query
    
    :param session: session within which update occurs
    :param model: table model
    :param oldinstance: instance of table model which was found in the db
    :param newinstance: instance of table model with updated fields
    :param skipcolumns: list of column names to update
    :rtype: boolean indicates whether any fields have changed
    '''

    updated = False
    
    # update all columns except those we were told to skip
    for col in object_mapper(newinstance).columns:
        # skip indicated keys
        if col.key in skipcolumns: continue
        
        # if any columns are different, update those columns
        # and return to the caller that it's been updated
        if getattr(oldinstance,col.key) != getattr(newinstance,col.key):
            setattr(oldinstance,col.key,getattr(newinstance,col.key))
            updated = True
    
    return updated

#----------------------------------------------------------------------
def insert_or_update(session, model, newinstance, skipcolumns=[], **kwargs):
#----------------------------------------------------------------------
    '''
    insert a new element or update an existing element based on kwargs query
    
    :param session: session within which update occurs
    :param model: table model
    :param newinstance: instance of table model which is to become representation in the db
    :param skipcolumns: list of column names to skip checking for any changes
    :param kwargs: query criteria
    '''


    # get instance, if it exists
    instance = getunique(session,model,**kwargs)
    
    # remember if we update anything
    updated = False

    # found a matching object, may need to update some of its attributes
    if instance is not None:
        updated = update(session,model,instance,newinstance,skipcolumns)
    
    # new object, just add to database
    else:
        session.add(newinstance)
        updated = True

    if updated:
        session.flush()
        
    return updated

#----------------------------------------------------------------------
def find_user(userid):
#----------------------------------------------------------------------
    '''
    find user in database
    
    :param userid: id or email address of user
    '''
    # if numeric, assume userid is id of user
    if type(userid) in [int,long]:
        return User.query.filter_by(id=userid).first()
    
    # if string assume email address
    if type(userid) in [str,unicode]:
        return User.query.filter_by(email=userid).first()
    
    # who knows what it was, but we didn't find it
    return None

########################################################################
class ApiCredentials(Base):
########################################################################
    __tablename__ = 'apicredentials'
    id = Column(Integer, Sequence('apicredentials_id_seq'), primary_key=True)
    name = Column(String(20), unique=True)
    key = Column(String(1024))
    secret = Column(String(1024))
    useraccesstokens = relationship('UserAccessToken',backref='apicredentials',cascade="all, delete")
    raceresultservices = relationship('RaceResultService',backref='apicredentials',cascade="all, delete")

    #----------------------------------------------------------------------
    def __init__(self, name=None, key=None, secret=None):
    #----------------------------------------------------------------------
        self.name = name
        self.key = key
        self.secret = secret
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<ApiCredentials %s %s %s>' % (self.name, self.key, self.secret)

########################################################################
class UserAccessToken(Base):
########################################################################
    __tablename__ = 'useraccesstoken'
    __table_args__ = (UniqueConstraint('user_id', 'apicredentials_id'),)
    id = Column(Integer, Sequence('useraccesstoken_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    apicredentials_id = Column(Integer, ForeignKey('apicredentials.id'))
    accesstoken = Column(String(1024))

    #----------------------------------------------------------------------
    def __init__(self, user_id=None, apicredentials_id=None, accesstoken=None):
    #----------------------------------------------------------------------
        self.user_id = User_id
        self.apicredentials_id = apicredentials_id
        self.accesstoken = accesstoken
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<UserAccessToken %s %s %s>' % (self.user_id, self.apicredentials_id, self.accesstoken)

########################################################################
# userrole associates user with their roles
########################################################################
# TODO: can't this be declared as a class using Base?
userrole_table = Table('userrole',metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('role_id', Integer, ForeignKey('role.id')),
    UniqueConstraint('user_id', 'role_id')
    )

########################################################################
# NOTE: for flask-security see https://pythonhosted.org/Flask-Security/quickstart.html#id1
class User(Base):
########################################################################
    __tablename__ = 'user'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    email = Column(String(255), unique=True)
    name = Column(String(120))
    pw_hash = Column(String(128))
    password = Column(String(255))
    active = Column(Boolean)

    # for Confirmable (see https://pythonhosted.org/Flask-Security/models.html)
    confirmed_at = Column(DateTime())

    # for Trackable (see https://pythonhosted.org/Flask-Security/models.html)
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(39))  # allow for IPv6
    current_login_ip = Column(String(39))  # allow for IPv6
    login_count = Column(Integer)

    #roles = relationship('userrole', backref='users', cascade="all, delete")
    #roles = relationship('Role', backref='users', secondary='userrole', cascade="all, delete")
    roles = relationship('Role', backref='users', secondary='userrole')
        # many to many pattern - see http://docs.sqlalchemy.org/en/rel_0_8/orm/relationships.html
    useraccesstokens = relationship('UserAccessToken',backref='user',cascade="all, delete")

    #----------------------------------------------------------------------
    def __init__(self, email, name, password, confirmed_at=None, last_login_at=None, current_login_at=None, last_login_ip=None, current_login_ip=None, login_count=0):
    #----------------------------------------------------------------------
        self.email = email
        self.name = name
        self.set_password(password)
        self.active = True
        self.confirmed_at = confirmed_at
        self.last_login_at = last_login_at
        self.current_login_at = current_login_at
        self.last_login_ip = last_login_ip
        self.current_login_ip = current_login_ip
        self.login_count = login_count

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<User %s %s>' % (self.email, self.name)

    #----------------------------------------------------------------------
    def set_password(self, password):
    #----------------------------------------------------------------------
        self.pw_hash = generate_password_hash(password)

    #----------------------------------------------------------------------
    def check_password(self, password):
    #----------------------------------------------------------------------
        return check_password_hash(self.pw_hash, password)
    
    ## the following methods are used by flask-login
    #----------------------------------------------------------------------
    def is_authenticated(self):
    #----------------------------------------------------------------------
        #return self.authenticated
        return True
    
    #----------------------------------------------------------------------
    def is_active(self):
    #----------------------------------------------------------------------
        return self.active
    
    #----------------------------------------------------------------------
    def is_anonymous(self):
    #----------------------------------------------------------------------
        return False
    
    #----------------------------------------------------------------------
    def get_id(self):
    #----------------------------------------------------------------------
        return self.id
    
    #----------------------------------------------------------------------
    def __eq__(self,other):
    #----------------------------------------------------------------------
        if isinstance(other, User):
            return self.get_id() == other.get_id()
        return NotImplemented
    
    #----------------------------------------------------------------------
    def __ne__(self,other):
    #----------------------------------------------------------------------
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal
    ## end of methods used by flask-login
    
########################################################################
# NOTE: for flask-security see https://pythonhosted.org/Flask-Security/quickstart.html#id1
class Role(Base):
########################################################################
    __tablename__ = 'role'
    __table_args__ = (UniqueConstraint('name', 'club_id'),)
    id = Column(Integer, Sequence('role_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(80))
    description = Column(db.String(255))

    #----------------------------------------------------------------------
    def __init__(self,name,description=None):
    #----------------------------------------------------------------------
        self.name = name
        self.description = description
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<Role %s %s>' % (Club.query.filter_by(id=self.club_id).first().shname, self.name)

########################################################################
class Club(Base):
########################################################################
    __tablename__ = 'club'
    id = Column(Integer, Sequence('club_id_seq'), primary_key=True)
    shname = Column(String(10), unique=True)
    name = Column(String(40), unique=True)
    memberserviceapi = Column(String(20))  # name from apicredentials table, None if no api configured
    memberserviceid = Column(String(64))  # identifies club to the member service
    location = Column(String(MAX_LOCATION_LEN))
    roles = relationship('Role',backref='club',cascade="all, delete")
    runners = relationship('Runner',backref='club',cascade="all, delete")
    races = relationship('Race',backref='club',cascade="all, delete")
    results = relationship('RaceResult',backref='club',cascade="all, delete")
    divisions = relationship('Divisions',backref='club',cascade="all, delete")
    series = relationship('Series',backref='club',cascade="all, delete")
    exclusions = relationship('Exclusion',backref='club',cascade="all, delete")

    #----------------------------------------------------------------------
    def __init__(self, shname=None, name=None, memberserviceapi=None, memberserviceid=None, location=None):
    #----------------------------------------------------------------------
        self.shname = shname
        self.name = name
        self.memberserviceapi = memberserviceapi
        self.memberserviceid = memberserviceid
        self.location = location
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<Club %s %s %s %s %s>' % (self.shname, self.name, self.memberserviceapi, self.memberserviceid, self.location)

########################################################################
class Runner(Base):
########################################################################
    '''
    * runner

    :param club_id: club.id
    :param name: runner's name
    :param dateofbirth: yyyy-mm-dd date of birth
    :param gender: M | F
    :param hometown: runner's home town
    :param member: True if member (default True)
    :param renewdate: yyyy-mm-dd date of renewal (default None)
    :param expdate: yyyy-mm-dd membership expiration date (default None)
    '''
    __tablename__ = 'runner'
    __table_args__ = (UniqueConstraint('name', 'dateofbirth', 'club_id'),)
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50))
    fname = Column(String(50))
    lname = Column(String(50))
    dateofbirth = Column(String(10))
    gender = Column(String(1))
    hometown = Column(String(50))
    renewdate = Column(String(10))
    expdate = Column(String(10))
    member = Column(Boolean)
    active = Column(Boolean)
    results = relationship("RaceResult", backref='runner', cascade="all, delete, delete-orphan")
    aliases = relationship("RunnerAlias", backref='runner', cascade="all, delete, delete-orphan")

    #----------------------------------------------------------------------
    def __init__(self, club_id, name=None, dateofbirth=None, gender=None, hometown=None, member=True, renewdate=None, expdate=None, fname=None, lname=None):
    #----------------------------------------------------------------------
        try:
            if dateofbirth:
                dobtest = t.asc2dt(dateofbirth)
            # special handling for dateofbirth = None
            else:
                dateofbirth = ''
        except ValueError:
            raise parameterError, 'invalid dateofbirth {0}'.format(dateofbirth)
        
        try:
            if renewdate:
                dobtest = t.asc2dt(renewdate)
            # special handling for renewdate = None
            else:
                renewdate = ''
        except ValueError:
            raise parameterError, 'invalid renewdate {0}'.format(renewdate)
        
        self.club_id = club_id
        self.name = name    
        self.fname = fname    
        self.lname = lname    
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.hometown = hometown
        self.renewdate = renewdate
        self.expdate = expdate
        self.member = member
        self.active = True
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        if self.member:
            dispmem = 'member'
        else:
            dispmem = 'nonmember'
        if self.active:
            dispactive = 'active'
        else:
            dispactive = 'inactive'
        return "<Runner('%s','%s','%s','%s','%s','%s','%s')>" % (self.club_id, self.name, self.dateofbirth, self.gender, self.hometown, dispmem, dispactive)
    
########################################################################
class RunnerAlias(Base):
########################################################################
    __tablename__ = 'runneralias'
    __table_args__ = (UniqueConstraint('name', 'club_id'),)
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50))
    runnerid = Column(Integer, ForeignKey('runner.id'))

    #----------------------------------------------------------------------
    def __init__(self, club_id, name=None, runnerid=None):
    #----------------------------------------------------------------------
        self.name = name
        self.runnerid = runnerid    

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<RunnerAlias %s %s>' % (self.name, self.runnerid)

########################################################################
class Race(Base):
########################################################################
    '''
    Defines race for a club
    
    :param club_id: club.id
    :param name: race name
    :param year: year of race
    :param racenum: number of race within the year # deprecated, ignored
    :param date: yyyy-mm-dd date of race
    :param starttime: hh:mm start of race
    :param distance: race distance in miles
    :param surface: 'road','track','trail'
    :param locationid: location.id
    :param external: True if race is from an external source
    '''
    __tablename__ = 'race'
    __table_args__ = (UniqueConstraint('name', 'year', 'club_id', 'fixeddist'),)
    id = Column(Integer, Sequence('race_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(MAX_RACENAME_LEN))
    year = Column(Integer)
    racenum = Column(Integer)   # deprecated, ignored
    date = Column(String(10))
    starttime = Column(String(5))
    distance = Column(Float)
    fixeddist = Column(String(10))   # null or coerced with "{:.4g}".format(distance)
    surface = Column(Enum('road','track','trail',name='SurfaceType'))
    locationid = Column(Integer, ForeignKey('location.id'))
    external = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    results = relationship("RaceResult", backref='race', cascade="all, delete, delete-orphan")
    series = relationship("Series", backref='races', secondary="raceseries")

########################################################################
class Course(Base):
########################################################################
    '''
    Defines course
    
    :param club_id: club.id
    :param source: source of course - name not id
    :param sourceid: id of course within source
    :param name: course name
    :param distmiles: race distance in miles
    :param distkm: race distance in km
    :param surface: 'road','track','trail'
    :param location: location race took place City, ST (may have country information)
    '''
    __tablename__ = 'course'
    __table_args__ = (UniqueConstraint('club_id', 'source','sourceid'),)
    id = Column(Integer, Sequence('course_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    source = Column(String(20))
    sourceid = Column(String(128))
    name = Column(String(MAX_RACENAME_LEN))
    date = Column(String(10))
    distmiles = Column(Float)
    distkm = Column(Float)
    surface = Column(Enum('road','track','trail',name='SurfaceType'))
    location = Column(String(MAX_LOCATION_LEN))
    raceid = Column(Integer)

    #----------------------------------------------------------------------
    def __init__(self, club_id=None, source=None, sourceid=None, name=None, date=None, distmiles=None, distkm=None, surface=None, location=None):
    #----------------------------------------------------------------------

        self.club_id = club_id
        self.source = source
        self.sourceid = sourceid
        self.name = name
        self.date = date
        self.distmiles = distmiles
        self.distkm = distkm
        self.surface = surface
        self.location = location

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Course('%s','%s','%s','%s','%s','%s','%s','%s','%s')>" % (self.club_id, self.source, self.sourceid, self.name, self.date, self.distmiles, self.distkm, self.surface, self.location)
    
########################################################################
class Location(Base):
########################################################################
    '''
    cache for race location and distance from club location
    '''
    __tablename__ = 'location'
    id = Column(Integer, Sequence('location_id_seq'), primary_key=True)
    name = Column(String(MAX_LOCATION_LEN), unique=True)
    latitude = Column(Float)
    longitude = Column(Float)
    cached_at = Column(DateTime)   # when location was cached
    lookuperror = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, name=None, latitude=None, longitude=None, cached_at=None, lookuperror=False):
    #----------------------------------------------------------------------
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.cached_at = cached_at
        self.lookuperror = lookuperror
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<Location %s %s %s %s>' % (self.name, self.latitude, self.longitude, self.cached_at)

########################################################################
class Series(Base):
########################################################################
    '''
    * series (attributes)

    :param club_id: club.id
    :param name: series name
    :param year: year of series
    :param membersonly: True if series applies to club members only
    :param overall: True if overall results are to be calculated
    :param divisions: True if division results are to be calculated
    :param agegrade: True if age graded results are to be calculated
    :param orderby: text name of RaceResult field to order results by
    :param hightolow: True if results should be ordered high to low based on orderby field
    :param allowties: True if ties are allowed
    :param averagetie: True if points for ties are to be averaged, else higher points awarded to all tied results
    :param maxraces: if set, maximum number of races which are included in total (if not set, all races are included)
    :param multiplier: multiply base point total by this value
    :param maxgenpoints: if set, this is the max points for first place within a gender (before multiplier)
    :param maxdivpoints: if set, this is the max points for first place within a division (before multiplier)
    :param maxbynumrunners: if True, max points is set based on number of runners
    :param description: describes series
    '''
    __tablename__ = 'series'
    __table_args__ = (UniqueConstraint('name','year','club_id'),)
    id = Column(Integer, Sequence('series_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50))
    year = Column(Integer)
    membersonly = Column(Boolean)
    calcoverall = Column(Boolean)
    calcdivisions = Column(Boolean)
    calcagegrade = Column(Boolean)
    orderby = Column(String(15))
    hightolow = Column(Boolean)
    allowties = Column(Boolean)
    averagetie = Column(Boolean)
    maxraces = Column(Integer)
    multiplier = Column(Integer)
    maxgenpoints = Column(Integer)
    maxdivpoints = Column(Integer)
    maxbynumrunners = Column(Boolean)
    active = Column(Boolean, default=True)
    description = Column(String(20))
    divisions = relationship("Divisions", backref='series', cascade="all, delete, delete-orphan")
    # races = relationship("Series", secondary="raceseries", backref='series')
    results = relationship("RaceResult", backref='series', cascade="all, delete, delete-orphan")


########################################################################
class ManagedResult(Base):
########################################################################
    '''
    Raw results from original official results, annotated with user's
    disposition about whether each row should be included in standings
    results, which are recorded in :class:`RaceResult`
    
    disposition
    
    * exact - exact name match found in runner table, with age consistent with dateofbirth
    * close - close name match found, with age consistent with dateofbirth
    * missed - close name match found, but age is inconsistent with dateofbirth
    * excluded - this name is in the exclusion table, either prior to import or as a result of user decision
    * '' - this means zero possible matches were found
    
    runnerid is set if found exact or close match, or if user includes this, null or '' otherwise
    '''
    __tablename__ = 'managedresult'
    #__table_args__ = (UniqueConstraint('runnername', 'raceid', 'club_id'),)
    id = Column(Integer, Sequence('results_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    raceid = Column(Integer, ForeignKey('race.id'))
    
    # from official race result file
    place = Column(Float)
    name = Column(String(50))
    fname = Column(String(50))
    lname = Column(String(50))
    gender = Column(String(1))
    age = Column(Integer)
    city = Column(String(50))
    state = Column(String(2))
    hometown = Column(String(50))
    club = Column(String(20))
    time = Column(Float)
    
    # metadata
    runnerid = Column(Integer, ForeignKey('runner.id'), nullable=True)
    #initialdisposition = Column(Enum('definite','similar','missed','excluded','',name='disposition_type'))
    initialdisposition = Column(String(15))
    confirmed = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, club_id, raceid, place=None, name=None, fname=None, lname=None,
                 gender=None,age=None,city=None,state=None,club=None,
                 time=None,
                 runnerid=None,initialdisposition=None,selectionmethod=None):
    #----------------------------------------------------------------------
        self.club_id = club_id
        self.raceid = raceid
        self.place = place
        self.name = name
        self.fname = fname
        self.lname = lname
        self.gender = gender
        self.age = age
        self.city = city
        self.state = state
        self.club = club
        self.time = time
        self.runnerid = runnerid
        self.initialdisposition = initialdisposition
        self.selectionmethod = selectionmethod

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<ManagedResult('%s','%s','%s','%s')>" % (self.raceid, self.place, self.name, self.time)

########################################################################
class RaceResultService(Base):
########################################################################
    __tablename__ = 'raceresultservice'
    id = Column(Integer, Sequence('raceresultservice_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    apicredentials_id = Column(Integer, ForeignKey('apicredentials.id'))
    attrs = Column(String(200)) # json object with attribute items

    #----------------------------------------------------------------------
    def __init__(self, club_id=None, apicredentials_id=None, attrs=None):
    #----------------------------------------------------------------------
        self.club_id = club_id
        self.apicredentials_id = apicredentials_id
        self.attrs = attrs
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<RaceResultService %s %s %s>' % (self.club_id, self.apicredentials_id, self.attrs)

########################################################################
class RaceResult(Base):
########################################################################
    '''
    :param club_id: club.id
    :param runnerid: runner.id
    :param raceid: race.id
    :param seriesid: series.id
    :param time: time in seconds
    :param gender: M or F
    :param agage: age on race day
    :param divisionlow: inclusive age at low end of division (may be 0)
    :param divisionhigh: inclusive age at high end of division (may be 99)
    :param overallplace: runner's place in race overall
    :param genderplace: runner's place in race within gender
    :param runnername: only used if runner is not in 'runner' table - if used, set runnerid to 0
    :param divisionplace: runner's place in race within division (see division table) - default None
    :param overallpoints: runner's point score from place overall, adjusted for rendering by series rules
    :param genderpoints: runner's point score from place within gender, adjusted for rendering by series rules
    :param divisionpoints: runner's point score from place within division, adjusted for rendering by series rules
    :param agtime: age grade time in seconds - default None
    :param agpercent: age grade percentage - default None
    :param source: references source of result data - name not id
    :param sourceid: references runner within source
    :param fuzzyage: set to 'y' if age math is "fuzzy", for sources which only have 5 year age groups listed
    :param instandings: boolean - default False
    :param hidden: boolean - true if hidden from raceresults analysis
    '''
    __tablename__ = 'raceresult'
    __table_args__ = (UniqueConstraint('runnerid', 'runnername', 'raceid', 'seriesid', 'club_id'),)
    id = Column(Integer, Sequence('raceresult_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    runnerid = Column(Integer, ForeignKey('runner.id'), index=True)
    runnername = Column(String(50)) # *** do not use!
    raceid = Column(Integer, ForeignKey('race.id'))
    seriesid = Column(Integer, ForeignKey('series.id'))
    gender = Column(String(1))
    agage = Column(Integer)
    divisionlow = Column(Integer)
    divisionhigh = Column(Integer)
    time = Column(Float)
    agfactor = Column(Float)
    agtime = Column(Float)
    agpercent = Column(Float)
    overallplace = Column(Float)
    genderplace = Column(Float)
    divisionplace = Column(Float)
    overallpoints = Column(Float)
    genderpoints = Column(Float)
    divisionpoints = Column(Float)
    agtimeplace = Column(Float)
    source = Column(String(20))
    sourceid = Column(String(128))
    sourceresultid = Column(String(128))
    fuzzyage = Column(Boolean)
    instandings = Column(Boolean)   
    hidden = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, club_id, runnerid, raceid, seriesid, time, gender, agage, divisionlow=None, divisionhigh=None,
                 overallplace=None, genderplace=None, runnername=None, divisionplace=None,
                 overallpoints=None, genderpoints=None, divisionpoints=None,
                 agtimeplace=None, agfactor=None, agtime=None, agpercent=None, 
                 source=None, sourceid=None, sourceresultid=None, fuzzyage=None,
                 instandings=False, hidden=False):
    #----------------------------------------------------------------------
        
        self.club_id = club_id
        self.runnerid = runnerid
        self.raceid = raceid
        self.seriesid = seriesid
        self.runnername = runnername
        self.time = time
        self.gender = gender
        self.agage = agage
        self.divisionlow = divisionlow
        self.divisionhigh = divisionhigh
        self.overallplace = overallplace
        self.genderplace = genderplace
        self.divisionplace = divisionplace
        self.overallpoints = overallpoints
        self.genderpoints = genderpoints
        self.divisionpoints = divisionpoints
        self.agtimeplace = agtimeplace
        self.agfactor = agfactor
        self.agtime = agtime
        self.agpercent = agpercent
        self.source = source
        self.sourceid = sourceid
        self.sourceresultid = sourceresultid
        self.fuzzyage = fuzzyage
        self.instandings = instandings
        self.hidden = hidden

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        # TODO: too many unlabeled fields -- need to make this clearer
        return "<RaceResult('%s','%s','%s','%s','%s','%s',div='(%s,%s)','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s', '%s')>" % (
            self.runnerid, self.runnername, self.raceid, self.seriesid, self.gender, self.agage, self.divisionlow, self.divisionhigh,
            self.time, self.overallplace, self.genderplace, self.divisionplace, self.agtimeplace, self.agfactor, self.agtime, self.agpercent,
            self.source, self.sourceid, self.sourceresultid,
            self.instandings, self.hidden)
    
########################################################################
class RaceSeries(Base):
########################################################################
    '''
    * raceseries
        * race/id
        * series/id
   
    :param raceid: race.id
    :param seriesid: series.id
    '''
    __tablename__ = 'raceseries'
    __table_args__ = (UniqueConstraint('raceid', 'seriesid'),)
    id = Column(Integer, Sequence('raceseries_id_seq'), primary_key=True)
    raceid = Column(Integer, ForeignKey('race.id'))
    seriesid = Column(Integer, ForeignKey('series.id'))
    active = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, raceid, seriesid):
    #----------------------------------------------------------------------
        
        self.raceid = raceid
        self.seriesid = seriesid
        self.active = True

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<RaceSeries(race='%s',series='%s',active='%s')>" % (self.raceid, self.seriesid, self.active)
    
########################################################################
class Divisions(Base):
########################################################################
    '''
    Divisions for indicated year, series
    
    :param club_id: club.id
    :param year: year of series
    :param seriesid: series.id
    :param divisionlow: low age in division
    :param divisionhigh: high age in division
    '''
    __tablename__ = 'divisions'
    id = Column(Integer, Sequence('divisions_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    year = Column(Integer)
    seriesid = Column(Integer, ForeignKey('series.id'))
    divisionlow = Column(Integer)
    divisionhigh = Column(Integer)
    active = Column(Boolean, default=True)


########################################################################
class Exclusion(Base):
########################################################################
    '''
    Close names found matching a member, which are not the member runner
    
    :param club_id: club.id
    :param foundname: name found in race result which is not member
    :param runnerid: runner.id
    '''
    __tablename__ = 'exclusion'
    __table_args__ = (UniqueConstraint('foundname', 'runnerid', 'club_id'),)
    id = Column(Integer, Sequence('divisions_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    foundname = Column(String(40))
    runnerid = Column(Integer, ForeignKey('runner.id'))

    #----------------------------------------------------------------------
    def __init__(self, club_id, foundname, runnerid):
    #----------------------------------------------------------------------
        
        self.club_id = club_id
        self.foundname = foundname
        self.runnerid = runnerid

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Exclusion '%s','%s')>" % (self.foundname, self.runnerid)

#####################################################
# for use in ColumnDT declarations
#####################################################
def renderfloat(expr, numdigits):
    return func.round(expr, numdigits)

def rendermember(expr):
    return case(
        [
            (expr==True, 'member'),
        ],
        else_='nonmember'
    )


class RenderTime(TypeDecorator):
    impl = types.String

    # assumes float value seconds to be converted to time
    def process_result_value(self, value, engine):
        return render.rendertime(float(value), 0)

def rendertime(expr):
    return cast(expr, RenderTime())


class RenderLocation(TypeDecorator):
    impl = types.String

    # assumes float value seconds to be converted to time
    def process_result_value(self, value, engine):
        loc = Location.query.filter_by(id=value).one_or_none()
        if loc:
            return loc.name
        else:
            return ''

def renderlocation(expr):
    return cast(expr, RenderLocation())


class RenderSeries(TypeDecorator):
    impl = types.String

    # assumes float value seconds to be converted to time
    def process_result_value(self, value, engine):
        series = Series.query.filter_by(id=value).one_or_none()
        if series:
            return series.name
        else:
            return ''

def renderseries(expr):
    return cast(expr, RenderSeries())

