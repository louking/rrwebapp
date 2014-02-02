#!/usr/bin/python
###########################################################################################
# authmodel - authentication portion of the database model
#
#	Date		Author		Reason
#	----		------		------
#       01/07/14        Lou King        Create
#
#   Copyright 2014 Lou King
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
authmodel - authentication portion of the database model
===============================================================
OBSOLETE -- now these tables are in racedb

'''
# pypi
from werkzeug.security import generate_password_hash, check_password_hash

# homegrown
from database import Base,Table,Column,Integer,Float,Boolean,String,Sequence,UniqueConstraint,ForeignKey,metadata,object_mapper,relationship,backref

rolenames = ['admin','viewer']

# TODO: this is dangerous because it will dropall tables -- need to fix that before uncommenting
##----------------------------------------------------------------------
#def init_owner(owner,ownername,ownerpw):
##----------------------------------------------------------------------
#    '''
#    recreate user,role,userrole tables for owner
#    
#    owner gets all roles
#    
#    :param owner: email address of database owner
#    :param ownername: name of owner
#    :param ownerpw: initial password for owner
#    :param rolenames: list of names of roles which will be allowed - owner gets all of these. default = {}
#    '''.format(rolenames)
#
#    # clear user, role, userrole tables
#    tablenames = ['user','role','userrole','club']
#    tables = []
#    for tablename in tablenames:
#        tables.append(metadata.tables[tablename])
#    metadata.drop_all(db.engine, tables=tables)
#    metadata.create_all(db.engine, tables=tables)
#    
#    # set up FSRC club
#    ownerclub = Club('owner','owner')
#    club = Club('fsrc','Frederick Steeplechaser Running Club')
#    db.session.add(ownerclub)
#    db.session.add(club)
#    
#    # set up roles for global, fsrc
#    roles = []
#    role = Role('owner')
#    ownerclub.roles.append(role)
#    roles.append(role)
#    for rolename in rolenames:
#        role = Role(rolename)
#        club.roles.append(role)
#        roles.append(role)
#    
#    # set up owner user, with appropriate roles
#    user = User(owner,ownername,ownerpw)
#    for role in roles:
#        user.roles.append(role)
#    db.session.add(user)
#    
#    db.session.commit()

########################################################################
# userrole associates user with their roles
########################################################################
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
    authenticated = Column(Boolean) # TODO: is this needed?
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
class Role(Base):
########################################################################
    __tablename__ = 'role'
    id = Column(Integer, Sequence('role_id_seq'), primary_key=True)
    name = Column(String(10))
    club_id = Column(Integer, ForeignKey('club.id'))
    UniqueConstraint('name', 'club_id')

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

    #----------------------------------------------------------------------
    def __init__(self,shname=None,name=None):
    #----------------------------------------------------------------------
        self.shname = shname
        self.name = name
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return '<Club %s %s>' % (self.shname,self.name)

