"""
userrole - manage users and roles
==================================
"""
# standard
import traceback

# pypi
import flask
from flask import current_app
import flask_login as flasklogin
from flask_login import login_required
from flask.views import MethodView

# home grown
from . import bp
from ...model import User
from ...accesscontrol import owner_permission
from ...model import db
from ... import user_datastore

# module specific needs
from ...model import User, Role, Club
from ...forms import UserForm, UserSettingsForm

########################################################################
# Manage Users
########################################################################
#----------------------------------------------------------------------
@bp.route('/manageusers')
@flasklogin.login_required
@owner_permission.require()
def manageusers():
#----------------------------------------------------------------------
    try:
        users = []
        for user in User.query.all():
            users.append((user.name,user)) # sort by name
        users.sort()
        users = [user[1] for user in users]

        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.render_template('manageusers.html',users=users)

#----------------------------------------------------------------------
@bp.route('/newuser', methods=['GET', 'POST'])
@flasklogin.login_required
@owner_permission.require()
def newuser():
#----------------------------------------------------------------------
    try:
        
        # create the form
        form = UserForm()
        form.club.choices = [(0,'Select Club')] + [(club.id,club.name) for club in Club.query.order_by('name') if club.name != 'owner']
    
        # set up buttons
        buttontext = 'Next >'
        
        # nothing to do for GET yet
        if flask.request.method == "GET":
            pass
    
        # validate form input
        elif flask.request.method == "POST":
            if form.validate_on_submit():
                # action and commit requested
                if flask.request.form['whichbutton'] == buttontext:
                    thisuser = user_datastore.create_user(
                        email=form.email.data, 
                        password=form.password.data)
                    thisuser.name = form.name.data
                    _setpermission(None, thisuser, 'owner', form.owner.data)
                    
                    flask.get_flashed_messages()    # clears flash queue

                    # roll back database updates and close transaction
                    db.session.commit()
                    return flask.redirect(flask.url_for('.useraction',userid=thisuser.id,action='edit'))
    
                # cancel requested - note changes may have been made in url_for('._setpermission') which need to be rolled back
                # TODO: get rid of this???  It should not work
                elif flask.request.form['whichbutton'] == 'Cancel':
                    #db.session.expunge_all() # throw out any changes which have been made
                    return flask.redirect(flask.url_for('.manageusers'))
    
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.render_template('ownermanageuser.html', form=form, thispagename='New User', action=flask.escape(buttontext), newuser=True)

#----------------------------------------------------------------------
@bp.route('/user/<userid>/<action>', methods=['GET','POST'])
@flasklogin.login_required
@owner_permission.require()
def useraction(userid,action):
#----------------------------------------------------------------------
    '''
    handle user record actions
    
    :param userid: user id
    :param action: 'delete' or 'edit'
    '''
    # get the user from the database
    thisuser = User.query.filter_by(id=userid).first()

    if action == 'delete':
        pagename = 'Delete User'
        buttontext = 'Delete'
        flask.flash('Confirm delete by pressing Delete button')
        successtext = '{} deleted'.format(thisuser.name)
        displayonly = True
        cancancel = True
    elif action == 'edit':
        pagename = 'Edit User'
        buttontext = 'Update'
        successtext = '{} updated'.format(thisuser.name)
        displayonly = False
        cancancel = False
    else:
        flask.abort(404)

    try:        
        # create the form
        form = UserForm(email=thisuser.email, name=thisuser.name)
        form.hidden_userid.data = userid
        form.club.choices = [(0,'Select Club')] + [(club.id,club.name) for club in Club.query.order_by('name') if club.name != 'owner']
    
        # define form for GET
        if flask.request.method == "GET" and not displayonly:
            form.owner.data = False
            for role in thisuser.roles:
                if role.name == 'owner':
                    form.owner.data = True
                    break
            form.admin.data = False
            form.viewer.data = False
        
        # validate form input
        elif flask.request.method == "POST":
            if form.validate_on_submit():
                flask.get_flashed_messages()    # clears flash queue
    
                # action and commit requested
                if flask.request.form['whichbutton'] == buttontext:
                    if action == 'delete':
                        db.session.delete(thisuser)
                    elif action =='edit':
                        thisuser.email = form.email.data
                        thisuser.name = form.name.data
                        if form.password.data:
                            thisuser.set_password(form.password.data)
                        _setpermission(None,thisuser,'owner',form.owner.data)
                        
                    # commit database updates and close transaction
                    db.session.commit()
                    return flask.redirect(flask.url_for('.manageusers'))
                
                # cancel requested - note changes may have been made in url_for('updatepermissions') which need to be rolled back
                # TODO: get rid of this???  It should not work
                elif flask.request.form['whichbutton'] == 'Cancel':
                    # db.session.expunge_all() # throw out any changes which have been made
                    return flask.redirect(flask.url_for('.manageusers'))
    
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.render_template('ownermanageuser.html', form=form,
                                 userurl=flask.url_for('.useraction',userid=userid,action=action),
                                 displayonly=displayonly,
                                 cancancel=cancancel,
                                 thispagename=pagename, action=buttontext)

#######################################################################
class UserSettings(MethodView):
#######################################################################
    decotrators = [login_required]
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        '''
        update user settings
        '''
        try:
            # get the user from the database
            userid = flask.session['_user_id']
            thisuser = User.query.filter_by(id=userid).first()
        
            pagename = 'User Settings'
            buttontext = 'Update'
            # successtext = '{} updated'.format(thisuser.name)
            displayonly = False
        
            # create the form
            form = UserSettingsForm(email=thisuser.email, name=thisuser.name)
            form.hidden_userid.data = userid
        
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('usersettings.html', form=form,
                                         userurl=flask.url_for('.usersettings'),
                                         displayonly=displayonly,
                                         thispagename=pagename, action=buttontext)
            
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            flask.flash(cause)
            current_app.logger.error(traceback.format_exc())
            raise
    

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        '''
        update user settings
        '''
        try:
            # get the user from the database
            userid = flask.session['_user_id']
            thisuser = User.query.filter_by(id=userid).first()
        
            pagename = 'User Settings'
            buttontext = 'Update'
            successtext = '{} updated'.format(thisuser.name)
            displayonly = False
        
            # create the form
            form = UserSettingsForm(email=thisuser.email, name=thisuser.name)
            form.hidden_userid.data = userid
        
            # 
            if form.validate_on_submit():
                flask.get_flashed_messages()    # clears flash queue
    
                # action and commit requested
                if flask.request.form['whichbutton'] == buttontext:
                    thisuser.email = form.email.data
                    thisuser.name = form.name.data
                    if form.password.data:
                        thisuser.set_password(form.password.data)

                    # commit database updates and close transaction
                    db.session.commit()
                    return flask.redirect(flask.request.args.get('next') or flask.url_for('frontend.index'))
                
                # cancel requested - note changes may have been made in url_for('updatepermissions') which need to be rolled back
                # TODO: get rid of this???  It should not work
                elif flask.request.form['whichbutton'] == 'Cancel':
                    db.session.rollback() # throw out any changes which have been made
                    return flask.redirect(flask.request.args.get('next') or flask.url_for('frontend.index'))
        
            # commit database updates and close transaction
            db.session.commit()
            return (flask.redirect(flask.request.args.get('next')) or flask.url_for('frontend.index'))
            
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            flask.flash(cause)
            current_app.logger.error(traceback.format_exc())
            raise
#----------------------------------------------------------------------
bp.add_url_rule('/usersettings/',view_func=UserSettings.as_view('usersettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#----------------------------------------------------------------------
def _setpermission(club,user,rolename,setrole):
#----------------------------------------------------------------------
    '''
    sets (or resets) a permission, but does not commit to the database
    
    :param club: club database object (or None if rolename=='owner')
    :param user: user database object
    :param rolename: name of role
    :param setrole: True to add the permission or False to remove it
    
    :rtype: boolean indicating success (True) or failure (False)
    '''
    # get the role
    if rolename=='owner':
        club = Club.query.filter_by(name='owner').first()
    thisrole = Role.query.filter_by(club_id=club.id, name=rolename).one_or_none()
    
    # not found -- must be first attempt to use role for club -- create it
    if not thisrole:
        role = Role(rolename)
        db.session.add(role)
        club.roles.append(role)
        db.session.flush()
        # try again
        thisrole = Role.query.filter_by(club_id=club.id, name=rolename).one()
    
    # adding the permission
    if setrole:
        # not clear why the next line doesn't work, see #498
        # if thisrole not in user.roles:
        if thisrole.id not in [r.id for r in user.roles]:
            user.roles.append(thisrole)
    
    # removing the permission
    else:
        # not clear why the next line doesn't work, see #498
        # if thisrole in user.roles:
        if thisrole.id in [r.id for r in user.roles]:
            user.roles.remove(thisrole)
    
    return True

#----------------------------------------------------------------------
@bp.route('/_setpermission')
@flasklogin.login_required
@owner_permission.require()
def _set_permission():
#----------------------------------------------------------------------
    '''
    ajax server side to set a permission on an existing user
    '''
    try:
        clubid = flask.request.args.get('clubid',0,type=int)
        userid = flask.request.args.get('userid',0,type=int)
        rolename = flask.request.args.get('rolename','')
        setrole = flask.request.args.get('setrole','false')=='true'
        
        if userid==0 or rolename=='':
            return flask.jsonify(success=False)
        
        # get the user and club
        thisuser = User.query.filter_by(id=userid).first()
        if rolename == 'owner':
            thisclub = Club.query.filter_by(name='owner').first()
        else:
            thisclub = Club.query.filter_by(id=clubid).first()
        
        # handle setting of permission for this club in the user object
        success = _setpermission(thisclub,thisuser,rolename,setrole)
    
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.jsonify(success=success)
    
#----------------------------------------------------------------------
@bp.route('/_getpermissions')
@flasklogin.login_required
@owner_permission.require()
def _get_permissions():
#----------------------------------------------------------------------
    '''
    ajax server side to get permissions for an existing user/club
    '''
    try:
        clubid = flask.request.args.get('clubid',0,type=int)
        userid = flask.request.args.get('userid',0,type=int)
        
        # get the user and club
        thisuser = User.query.filter_by(id=userid).first()
    
        # set up false permissions
        # NOTE: permissions need to match model.rolenames
        admin = False
        viewer = False
        
        if clubid != 0 and thisuser:
            for role in thisuser.roles:
                if role.club_id == clubid:
                    if   role.name == 'admin':  admin = True
                    elif role.name == 'viewer': viewer = True
                
        # commit database updates and close transaction
        db.session.commit()
        
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

    return flask.jsonify(admin=admin,viewer=viewer)
    
