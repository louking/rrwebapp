###########################################################################################
# login -- log in / out views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/11/13        Lou King        Create
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

# standard
import datetime
import time
from functools import wraps

# pypi
import flask
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user
from flask.ext.principal import Identity, AnonymousIdentity, identity_changed, identity_loaded, UserNeed, RoleNeed
import flask.ext.wtf as flaskwtf
import wtforms

# home grown
from . import app
import racedb
from racedb import User,Club
from nav import getuserclubs
from database_flask import db   # this is ok because this module only runs under flask
from loutilities import timeu
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission

login_manager = LoginManager(app)
login_manager.login_view = 'login'

########################################################################
########################################################################
#----------------------------------------------------------------------
@login_manager.user_loader
def load_user(userid):
#----------------------------------------------------------------------
    '''
    required by flask-login
    
    :param userid: email address of user
    '''
    # Return an instance of the User model
    user = racedb.find_user(userid)
    #if hasattr(user,'email'):
    #    login_manager.login_message = '{}: logged in'.format(user.email)
    return user

########################################################################
class LoginForm(flaskwtf.Form):
########################################################################
    email = wtforms.StringField()
    password = wtforms.PasswordField()

#----------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
#----------------------------------------------------------------------
    # define form
    form = LoginForm()

    # Validate form input 
    #if flask.request.method == "POST" and form.validate_on_submit():
    if form.validate_on_submit():
        try:
            # Retrieve the user from the datastore
            user = racedb.find_user(form.email.data)
            
            # flag user doesn't exist or incorrect password
            if not (user and user.check_password(form.password.data)):
                return flask.render_template('login.html', form=form, error='username or password invalid')
    
            # we're good
            # Keep the user info in the session using Flask-Login
            login_user(user)
            flask.session['logged_in'] = True
            flask.session['user_name'] = user.name
            flask.session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(minutes=120)
    
            # Tell Flask-Principal the identity changed
            identity_changed.send(
                flask.current_app._get_current_object(),
                identity = Identity(user.id))
            
            userclubs = getuserclubs(user)
            
            # zero clubs is an internal error in the databse
            if not(userclubs):
                abort(500)  # Internal Server Error
                
            # give user access to the first club in the list
            club = Club.query.filter_by(id=userclubs[0][0]).first()
            flask.session['club_id'] = club.id
            flask.session['club_name'] = club.name
            
            # set default year to be current year
            today = timeu.epoch2dt(time.time())
            flask.session['year'] = today.year
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.redirect(flask.request.args.get('next') or flask.url_for('index'))
        
        except:
           # roll back database updates and close transaction
            db.session.rollback()
            raise
    
    return flask.render_template('login.html', form=form)

########################################################################
########################################################################
#----------------------------------------------------------------------
def set_logged_out():
#----------------------------------------------------------------------
    logout_user()
    for key in ('logged_in','user_name','club_id','club_name'):
        flask.session.pop(key, None)
        
    for key in ('identity.name', 'identity.auth_type'):
        flask.session.pop(key, None)

#----------------------------------------------------------------------
@app.route('/logout')
def logout():
#----------------------------------------------------------------------
    try:
        # Remove the user information from the session, if not already logged out
        if 'user_id' in flask.session:
            user = racedb.find_user(flask.session['user_id'])
            #user.authenticated = False
            set_logged_out()
        
            # Tell Flask-Principal the user is anonymous
            identity_changed.send(flask.current_app._get_current_object(),
                                  identity=AnonymousIdentity())
    
        # commit database updates and close transaction
        db.session.commit()
        return flask.redirect(flask.request.args.get('next') or flask.url_for('index'))
    
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

#----------------------------------------------------------------------
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
#----------------------------------------------------------------------
    try:
        # Set the identity user object
        identity.user = current_user
        if not current_user.is_authenticated():
            set_logged_out()
    
        # Add the UserNeed to the identity
        if hasattr(current_user, 'id'):
            identity.provides.add(UserNeed(current_user.id))
    
        # Assuming the User model has a list of roles, update the
        # identity with the roles that the user provides
        if hasattr(current_user,'roles'):
            for role in current_user.roles:
                if role.name == 'viewer' or role.name == 'admin':
                    identity.provides.add(ViewClubDataNeed(role.club.id))
                elif role.name == 'admin':
                    identity.provides.add(UpdateClubDataNeed(role.club.id))
                elif role.name == 'owner':
                    identity.provides.add(RoleNeed('owner'))
                    for club in racedb.Club.query.all():
                        if club.name == 'owner': continue
                        identity.provides.add(ViewClubDataNeed(club.id))
                        identity.provides.add(UpdateClubDataNeed(club.id))
        
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

########################################################################
class ClubForm(flaskwtf.Form):
########################################################################
    club = wtforms.SelectField('Club',coerce=int)

#----------------------------------------------------------------------
@app.route('/setclub', methods=['GET', 'POST'])
@login_required
def setclub():
#----------------------------------------------------------------------
    try:
        # find session's user
        thisuser = current_user
    
        # define form
        form = ClubForm()
        form.club.choices = getuserclubs(thisuser)
    
        # Validate form input for POST
        if flask.request.method == "POST" and form.validate_on_submit():
            # Retrieve the club picked by the user
            thisclubid = form.club.data
            club = Club.query.filter_by(id=thisclubid).first()
            flask.session['club_id'] = club.id
            flask.session['club_name'] = club.name
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.redirect(flask.request.args.get('next') or flask.url_for('index'))
        
        # commit database updates and close transaction
        db.session.commit()
        return flask.render_template('setclub.html', form=form, pagename='Set Club', action='Set Club')
    
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

########################################################################
class YearForm(flaskwtf.Form):
########################################################################
    year = wtforms.IntegerField('Year')

#----------------------------------------------------------------------
@app.route('/setyear', methods=['GET', 'POST'])
@login_required
def setyear():
#----------------------------------------------------------------------
    try:
        # find session's user
        thisuser = current_user
    
        # define form
        form = YearForm()
    
        # Validate form input
        if form.validate_on_submit():
            # Retrieve the year picked by the user
            year = form.year.data
            if type(year) != int or year < 2013 or year > 2050:
                error = 'invalid year'
                db.session.rollback()
                return flask.render_template('setyear.html', form=form, pagename='Set Year', action='Set Year', error=error)
            flask.session['year'] = year
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.redirect(flask.request.args.get('next') or flask.url_for('index'))
        
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.render_template('setyear.html', form=form, pagename='Set Year', action='Set Year')


