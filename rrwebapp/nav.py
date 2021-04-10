###########################################################################################
# nav - navigation 
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/17/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################
'''
nav - navigation
====================
helper functions and ajax APIs to support navigation and headers
'''

# standard
import json
from datetime import datetime

# pypi
from flask import url_for, abort, session
from flask_login import current_user
from flask.views import MethodView
from flask import request

# home grown
from . import app
from .racedb import Club, Race
from .apicommon import success_response, failure_response
from .accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from .database_flask import db   # this is ok because this module only runs under flask

# from http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
from io import StringIO
from html.parser import HTMLParser


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# get product name
productname = strip_tags(app.jinja_env.globals['_productname'])

#----------------------------------------------------------------------
def is_authenticated(user):
#----------------------------------------------------------------------
    # flask-login 3.x changed user.is_authenticated from method to property
    # we are not sure which flask-login we're using, so try method first, 
    # then property

    try:
        return user.is_authenticated()
    except TypeError:
        return user.is_authenticated

#----------------------------------------------------------------------
def getnavigation():
#----------------------------------------------------------------------
    '''
    retrieve navigation list, based on current club and user's roles
    
    :param rolenames: list of role names
    :rettype: list of dicts {'display':navdisplay,'url':navurl}
    '''
    thisuser = current_user

    # set club and club permissions
    club = None
    if 'club_id' in session:
        club = Club.query.filter_by(id=session['club_id']).first()
        readcheck = ViewClubDataPermission(session['club_id'])
        writecheck = UpdateClubDataPermission(session['club_id'])

    navigation = []
    
    navigation.append({'display':'{} Home'.format(productname),'url':url_for('index')})
    
    if is_authenticated(thisuser):
        if owner_permission.can():
            navigation.append({'display':'Clubs','url':url_for('manageclubs')})
            navigation.append({'display':'Users','url':url_for('manageusers')})
            navigation.append({'display':'Service Credentials','url':url_for('servicecredentials')})

            navigation.append({'display':'Results Analysis','list':[]})
            navigation[-1]['list'].append({'display':'Status/Control','url':url_for('resultsanalysisstatus')})
            navigation[-1]['list'].append({'display':'Summary','url':url_for('resultsanalysissummary')})
            navigation[-1]['list'].append({'display':'Services','url':url_for('raceresultservices')})
            navigation[-1]['list'].append({'display':'Courses','url':url_for('courses')})
            navigation[-1]['list'].append({'display':'Locations','url':url_for('locations')})
            
        if club and readcheck.can():
            navigation.append({'display':'Members','url':url_for('managemembers')})
            navigation.append({'display':'Races','url':url_for('manageraces')})
            navigation.append({'display':'Series','url':url_for('manageseries')})
            navigation.append({'display':'Divisions','url':url_for('managedivisions')})

            # owner check to avoid duplicate navigation
            if not owner_permission.can():
                navigation.append({'display':'Results Summary','url':url_for('resultsanalysissummary')})

        if club and writecheck.can():
            navigation.append({'display':'Exclusions','url':url_for('editexclusions')})
    
    # get club option list
    clubs = Club.query.all()
    clubnames = [club.name for club in clubs if club.name != 'owner']
    clubshnames = [club.shname for club in clubs if club.name != 'owner']
    clubopts = dict(list(zip(clubnames,clubshnames)))

    # update session based on arguments
    clubarg = request.args.get('club',None)
    yeararg = request.args.get('year',None)
    seriesarg = request.args.get('series',None)
    if clubarg:
        session['last_standings_club'] = clubarg
    if yeararg:
        session['last_standings_year'] = yeararg
    if seriesarg:
        session['last_standings_series'] = seriesarg

    # get defaults for navigation forms
    clubsess = session.get('last_standings_club',None)

    # what year is it now? what default should we use?
    thisyear = datetime.now().year
    yeardefault = session['last_standings_year'] if 'last_standings_year' in session else thisyear

    # anonymous access
    navigation.append({'display':'Standings','url':'#',
        'attr':[{'name':'_rrwebapp-editor-form',
                 'value': json.dumps({
                     'title': 'Choose Standings',
                     'editoropts': {
                         'className': 'choose-standings-form',
                         'fields': [
                             {'name': 'club', 'label': 'Club', 'type': 'select2', 'options': clubopts, 'def': clubsess},
                             {'name': 'year', 'label': 'Year', 'type': 'select2', 'options': list(range(2013, thisyear+1)), 'def':yeardefault},
                             {'name': 'series', 'label': 'Series', 'type': 'select2', 'opts': {'placeholder': 'Select series'}},
                         ]
                     },
                     'buttons': [
                         {'label': 'Show Standings',
                          'action': '''
                                    {{ 
                                        var args = {{club: this.get("club"), year: this.get("year"), series: this.get("series") }};
                                        var error = false;
                                        this.error("");
                                        for (var field in args) {{
                                            this.error(field, "");
                                            if (!args[field]) {{
                                                error = true;
                                                this.error(field, "must be supplied");
                                            }}
                                        }}
                                        if (error) {{
                                            this.error("check field errors");
                                            return;
                                        }}
                                        args.desc = this.field("club").inst().find(":selected").text() + " - " + this.get("year") + " " + this.get("series");
                                        this.close();
                                        window.location.href = "{}?\" + $.param( args );
                                    }}'''.format(url_for('viewstandings'))},
                     ],
                     # name of functions called with standalone editor instance and buttons field from above
                     'onopen': 'navstandingsopen',
                     'onclose': 'navstandingsclose',
                 })

        }

        ]})
    navigation.append({'display':'Results','url':'#',
        'attr':[{   'name':'_rrwebapp-editor-form',
                    'value': json.dumps({
                            'title' : 'Choose club',
                            'buttons' : [
                                {'label': 'table', 'action': '{{ var args = {{club: this.get("club") }}; window.location.href = "{}?\" + $.param( args ) }}'.format(url_for('results'))},
                                {'label': 'chart', 'action': '{{ var args = {{club: this.get("club") }}; window.location.href = "{}?\" + $.param( args ) }}'.format(url_for('resultschart'))},
                            ],
                            'editoropts': {
                                'fields': [ {
                                    'name': 'club',
                                    'label': 'Club:',
                                    'type': 'select', 'options': clubopts,
                                    'def': clubsess,
                                    },
                                ],
                            },
                            })
                  } ] 
    })

    if is_authenticated(thisuser):
        # TODO: when more tools are available, move writecheck to appropriate tools
        if club and writecheck.can():
            navigation.append({'display':'Tools','list':[]})
            navigation[-1]['list'].append({'display':'Normalize Members','url':url_for('normalizememberlist')})
            navigation[-1]['list'].append({'display':'Export Results','url':url_for('exportresults')})
    navigation.append({'display':'About','url':url_for('sysinfo')})
    
    if is_authenticated(thisuser) and owner_permission.can():
        navigation.append({'display':'Debug','url':url_for('debug')})
    
    return navigation

#----------------------------------------------------------------------
def getuserclubs(user):
#----------------------------------------------------------------------
    '''
    get clubs user has permissions for
    
    :param user: User record
    :rtype: [(club.id,club.name),...], not including 'owner' club, for select, sorted by club.name
    '''
    clubs = []
    for role in user.roles:
        thisclub = Club.query.filter_by(id=role.club_id).first()
        if thisclub.name == 'owner': continue
        clubselect = (thisclub.id,thisclub.name)
        if clubselect not in clubs:
            clubs.append(clubselect)
    decclubs = sorted([(club[1],club) for club in clubs])
    return [club[1] for club in decclubs]

#----------------------------------------------------------------------
def getuseryears(user):
#----------------------------------------------------------------------
    '''
    get years user can set
    NOTE: currently this works for all users
    
    :param user: User record
    :rtype: [(year,year),...], for select, sorted by year
    '''
    return [(y,y) for y in range(2013, datetime.now().year+1)]
            

#----------------------------------------------------------------------
def setnavigation():
#----------------------------------------------------------------------
    '''
    set navigation based on user, club
    '''
    thisuser = current_user

    club = None
    if hasattr(session,'club'):
        club = session.club
        
    # get navigation list
    session['nav'] = getnavigation()
    
    # update years and clubs choices
    if is_authenticated(thisuser):
        session['year_choices'] = getuseryears(thisuser)
        session['club_choices'] = getuserclubs(thisuser)

#######################################################################
class UserClubAPI(MethodView):
#######################################################################

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        """
        GET request at /_userclub/
        Return {'club_id':<session.club_id>, 'choices':[(<club_id>, <club_name>),...]}
        """
        try:
            if not is_authenticated(current_user):
                db.session.rollback()
                return failure_response({'error':403})
            
            # get unique clubs and sort the list
            decclubs_set = set([])
            for role in current_user.roles:
                if role.club.name == 'owner': continue
                decclubs_set.add((role.club.name,(role.club.id,role.club.name)))
            decclubs = sorted(decclubs_set)
            clubs = [c[1] for c in decclubs]
            
            response = success_response(club_id=session['club_id'],choices=clubs)

            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self,club_id):
    #----------------------------------------------------------------------
        """
        POST request at /_userclub/<club_id>
        Sets session.club_id
        """
        try:
            if not is_authenticated(current_user) or club_id not in [c[0] for c in getuserclubs(current_user)]:
                db.session.rollback()
                return failure_response({'error':403})
            
            session['club_id'] = club_id
            response = success_response()
            
            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

#----------------------------------------------------------------------
userclub_view = UserClubAPI.as_view('userclub_api')
app.add_url_rule('/_userclub/',view_func=userclub_view,methods=['GET'])
app.add_url_rule('/_userclub/<int:club_id>',view_func=userclub_view,methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class UserYearAPI(MethodView):
#######################################################################

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        """
        GET request at /_useryear/
        Return {'year':<session.year>, 'choices':[(<year>, <year>),...]}
        """
        try:
            if not is_authenticated(current_user):
                db.session.rollback()
                return failure_response({'error':403})

            years = getuseryears(current_user)

            response = success_response(year=session['year'],choices=years)

            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self,year):
    #----------------------------------------------------------------------
        """
        POST request at /_useryear/<year>/
        Sets session.year
        """
        try:
            if not is_authenticated(current_user) or year not in [y[0] for y in getuseryears(current_user)]:
                db.session.rollback()
                abort(403)

            session['year'] = year
            
            response = success_response()

            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

#----------------------------------------------------------------------
useryear_view = UserYearAPI.as_view('useryear_api')
app.add_url_rule('/_useryear/',view_func=useryear_view,methods=['GET'])
app.add_url_rule('/_useryear/<int:year>',view_func=useryear_view,methods=['POST'])
#----------------------------------------------------------------------

