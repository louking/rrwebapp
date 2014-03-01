#!/usr/bin/python
###########################################################################################
# racedb  -- manage race database
#
#	Date		Author		Reason
#	----		------		------
#       01/23/13        Lou King        Create
#       04/26/13        Lou King        temp fix for issue #20 - allow mysql+gaerdbms
#
#   Copyright 2013 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
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

# github

# other
from database import *

# home grown
import version
from loutilities import timeu

DBDATEFMT = '%Y-%m-%d'
t = timeu.asctime(DBDATEFMT)

class dbConsistencyError(Exception): pass

rolenames = ['admin','viewer']

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
# userrole associates user with their roles
########################################################################
# TODO: can't this be declared as a class using Base?
userrole_table = Table('userrole',metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('role_id', Integer, ForeignKey('role.id')),
    UniqueConstraint('user_id', 'role_id')
    )

########################################################################
class User(Base):
########################################################################
    __tablename__ = 'user'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    email = Column(String(120), unique=True)
    name = Column(String(120))
    pw_hash = Column(String(80))  # finding 66 characters on a couple of tests
    active = Column(Boolean)
    #authenticated = Column(Boolean) # TODO: is this needed?
    pwresetrequired = Column(Boolean)
    #roles = relationship('userrole', backref='users', cascade="all, delete")
    #roles = relationship('Role', backref='users', secondary='userrole', cascade="all, delete")
    roles = relationship('Role', backref='users', secondary='userrole')
        # many to many pattern - see http://docs.sqlalchemy.org/en/rel_0_8/orm/relationships.html

    #----------------------------------------------------------------------
    def __init__(self,email,name,password,pwresetrequired=False):
    #----------------------------------------------------------------------
        self.email = email
        self.name = name
        self.set_password(password)
        self.active = True
        self.authenticated = False      # not sure how this should be handled
        self.pwresetrequired = pwresetrequired
        
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
class Role(Base):
########################################################################
    __tablename__ = 'role'
    id = Column(Integer, Sequence('role_id_seq'), primary_key=True)
    name = Column(String(10))
    club_id = Column(Integer, ForeignKey('club.id'))
    __table_args__ = (UniqueConstraint('name', 'club_id'),)

    #----------------------------------------------------------------------
    def __init__(self,name):
    #----------------------------------------------------------------------
        self.name = name
        
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
    roles = relationship('Role',backref='club',cascade="all, delete")
    runners = relationship('Runner',backref='club',cascade="all, delete")
    races = relationship('Race',backref='club',cascade="all, delete")
    results = relationship('RaceResult',backref='club',cascade="all, delete")
    divisions = relationship('Divisions',backref='club',cascade="all, delete")
    series = relationship('Series',backref='club',cascade="all, delete")
    exclusions = relationship('Exclusion',backref='club',cascade="all, delete")

    #----------------------------------------------------------------------
    def __init__(self,shname=None,name=None):
    #----------------------------------------------------------------------
        self.shname = shname
        self.name = name
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<Club %s %s>' % (self.shname,self.name)

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
    '''
    __tablename__ = 'runner'
    __table_args__ = (UniqueConstraint('name', 'dateofbirth', 'club_id'),)
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50))
    dateofbirth = Column(String(10))
    gender = Column(String(1))
    hometown = Column(String(50))
    renewdate = Column(String(10))
    member = Column(Boolean)
    active = Column(Boolean)
    results = relationship("RaceResult", backref='runner', cascade="all, delete, delete-orphan")

    #----------------------------------------------------------------------
    def __init__(self, club_id, name, dateofbirth, gender, hometown, member=True, renewdate=None):
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
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.hometown = hometown
        self.renewdate = renewdate
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
class Race(Base):
########################################################################
    '''
    Defines race for a club
    
    :param club_id: club.id
    :param name: race name
    :param year: year of race
    :param racenum: number of race within the year
    :param date: yyyy-mm-dd date of race
    :param starttime: hh:mm start of race
    :param distance: race distance in miles
    :param surface: 'road','track','trail'
    '''
    __tablename__ = 'race'
    __table_args__ = (UniqueConstraint('name', 'year', 'club_id'),)
    id = Column(Integer, Sequence('race_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50))
    year = Column(Integer)
    racenum = Column(Integer)
    date = Column(String(10))
    starttime = Column(String(5))
    distance = Column(Float)
    surface = Column(Enum('road','track','trail',name='SurfaceType'))
    active = Column(Boolean)
    results = relationship("RaceResult", backref='race', cascade="all, delete, delete-orphan")
    series = relationship("RaceSeries", backref='race', cascade="all, delete, delete-orphan")

    #----------------------------------------------------------------------
    def __init__(self, club_id, year, name=None, racenum=None, date=None, starttime=None, distance=None, surface=None):
    #----------------------------------------------------------------------

        self.club_id = club_id
        self.name = name
        self.year = year
        self.racenum = racenum
        self.date = date
        self.starttime = starttime
        self.distance = distance
        self.surface = surface
        self.active = True

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Race('%s','%s','%s','%s','%s','%s','%s','%s',active='%s')>" % (self.club_id, self.name, self.year, self.racenum, self.date, self.starttime, self.distance, self.surface, self.active)
    
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
    :param averagetie: True if points for ties are to be averaged, else higher points awarded to all tied results
    :param maxraces: if set, maximum number of races which are included in total (if not set, all races are included)
    :param multiplier: multiply base point total by this value
    :param maxgenpoints: if set, this is the max points for first place within a gender (before multiplier)
    :param maxdivpoints: if set, this is the max points for first place within a division (before multiplier)
    :param maxbynumrunners: if True, max points is set based on number of runners
    '''
    __tablename__ = 'series'
    __table_args__ = (UniqueConstraint('name','year','club_id'),)
    id = Column(Integer, Sequence('series_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    name = Column(String(50),unique=True)
    year = Column(Integer)
    membersonly = Column(Boolean)
    calcoverall = Column(Boolean)
    calcdivisions = Column(Boolean)
    calcagegrade = Column(Boolean)
    orderby = Column(String(15))
    hightolow = Column(Boolean)
    averagetie = Column(Boolean)
    maxraces = Column(Integer)
    multiplier = Column(Integer)
    maxgenpoints = Column(Integer)
    maxdivpoints = Column(Integer)
    maxbynumrunners = Column(Boolean)
    active = Column(Boolean)
    divisions = relationship("Divisions", backref='series', cascade="all, delete, delete-orphan")
    races = relationship("RaceSeries", backref='series', cascade="all, delete, delete-orphan")
    results = relationship("RaceResult", backref='series', cascade="all, delete, delete-orphan")

    #----------------------------------------------------------------------
    def __init__(self, club_id, year, name=None, membersonly=None, overall=None, divisions=None, agegrade=None, orderby=None, hightolow=None, averagetie=None, maxraces=None, multiplier=None, maxgenpoints=None, maxdivpoints=None, maxbynumrunners=None):
    #----------------------------------------------------------------------
        
        self.club_id = club_id
        self.name = name
        self.membersonly = membersonly
        self.year = year
        self.calcoverall = overall
        self.calcdivisions = divisions
        self.calcagegrade = agegrade
        self.orderby = orderby
        self.hightolow = hightolow
        self.averagetie = averagetie
        self.maxraces = maxraces
        self.multiplier = multiplier
        self.maxgenpoints = maxgenpoints
        self.maxdivpoints = maxdivpoints
        self.maxbynumrunners = maxbynumrunners
        self.active = True

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Series('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s',active='%s')>" % (
            self.club_id, self.name, self.year, self.membersonly, self.calcoverall, self.calcdivisions, self.calcagegrade,
            self.orderby, self.hightolow, self.averagetie, self.maxraces, self.multiplier, self.maxgenpoints,
            self.maxdivpoints, self.maxbynumrunners, self.active
            )
    
########################################################################
class RaceResult(Base):
########################################################################
    '''

    
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
    :param agtime: age grade time in seconds - default None
    :param agpercent: age grade percentage - default None
    :param instandings: boolean - default False
    '''
    __tablename__ = 'raceresult'
    __table_args__ = (UniqueConstraint('runnerid', 'runnername', 'raceid', 'seriesid', 'club_id'),)
    id = Column(Integer, Sequence('raceresult_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    runnerid = Column(Integer, ForeignKey('runner.id'))
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
    agtimeplace = Column(Float)
    instandings = Column(Boolean)   # *** always True

    #----------------------------------------------------------------------
    def __init__(self, runnerid, raceid, seriesid, time, gender, agage, divisionlow=None, divisionhigh=None,
                 overallplace=None, genderplace=None, runnername=None, divisionplace=None,
                 agtimeplace=None, agfactor=None, agtime=None, agpercent=None, instandings=False):
    #----------------------------------------------------------------------
        
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
        self.agtimeplace = agtimeplace
        self.agfactor = agfactor
        self.agtime = agtime
        self.agpercent = agpercent
        self.instandings = instandings

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        # TODO: too many unlabeled fields -- need to make this clearer
        return "<RaceResult('%s','%s','%s','%s','%s','%s',div='(%s,%s)','%s','%s','%s','%s','%s','%s','%s','%s','%s')>" % (
            self.runnerid, self.runnername, self.raceid, self.seriesid, self.gender, self.agage, self.divisionlow, self.divisionhigh,
            self.time, self.overallplace, self.genderplace, self.divisionplace, self.agtimeplace, self.agfactor, self.agtime, self.agpercent,
            self.instandings)
    
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
    active = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, club_id, year, seriesid=None, divisionlow=None, divisionhigh=None):
    #----------------------------------------------------------------------
        
        self.club_id = club_id
        self.year = year
        self.seriesid = seriesid
        self.divisionlow = divisionlow
        self.divisionhigh = divisionhigh
        self.active = True

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Divisions '%s','%s','%s','%s','%s',active='%s')>" % (self.club_id, self.year, self.seriesid, self.divisionlow, self.divisionhigh, self.active)
    
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
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    '''
    test code for this module
    '''
    parser = argparse.ArgumentParser(version='{0} {1}'.format('runningclub',version.__version__))
    parser.add_argument('-m','--memberfile',help='file with member information',default=None)
    parser.add_argument('-r','--racefile',help='file with race information',default=None)
    args = parser.parse_args()
    
    OUT = open('racedbtest.txt','w')
    setracedb('testdb.db')
    sessaion = Session()

    if args.memberfile:
        import clubmember
        members = clubmember.ClubMember(args.memberfile)
        
        for name in members.getmembers():
            thesemembers = members.members[name]
            for thismember in thesemembers:
                runner = Runner(thismember['name'],thismember['dob'],thismember['gender'],thismember['hometown'])
                #if runner.name == 'Doug Batey':
                #    pdb.set_trace()
                added = insert_or_update(session,Runner,runner,skipcolumns=['id'],name=runner.name,dateofbirth=runner.dateofbirth)
                if added:
                    OUT.write('added or updated {0}\n'.format(runner))
                else:
                    OUT.write('no updates necessary {0}\n'.format(runner))
                
        session.commit()
        
        runners = session.query(Runner).all()
        for runner in runners:
            OUT.write('found id={0}, runner={1}\n'.format(runner.id,runner))
        
    if args.racefile:
        print 'needs update due to Race initializer change'
        return
        import racefile
        races = racefile.RaceFile(args.racefile)
        
        for race in races.getraces():
            newrace = Race(race['race'],race['year'],race['date'],race['time'],race['distance'])
            added = insert_or_update(session,Race,newrace,skipcolumns=['id'],name=newrace.name,year=newrace.year)
            if added:
                OUT.write('added or updated race {0}\n'.format(race))
            else:
                OUT.write ('no updates necessary {0}\n'.format(race))
        
        session.commit()
        
        dbraces = session.query(Race).all()
        for race in dbraces:
            OUT.write('found id={0}, race={1}\n'.format(race.id,race))
            
        #for series in races.series.keys():
        #    added = testdb.addseriesattributes(series,races.series[series])
        #    if added:
        #        OUT.write('added seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))
        #    else:
        #        OUT.write('did not add seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))

    session.close()
    OUT.close()
        
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()