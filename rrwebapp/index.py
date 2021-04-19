###########################################################################################
# index - just some boilerplate
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/04/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import smtplib
import urllib.request, urllib.parse, urllib.error

# pypi
import flask
from flask import make_response,request
from flask.views import MethodView

# home grown
from . import app
from .model import db   # this is ok because this module only runs under flask

# module specific needs
from .forms import FeedbackForm
from . import version

#######################################################################
class ViewIndex(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('index.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/',view_func=ViewIndex.as_view('index'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ViewFeatures(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('features.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/features',view_func=ViewFeatures.as_view('features'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ViewTerms(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('tos.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/termsofservice',view_func=ViewTerms.as_view('terms'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class GetFeedback(MethodView):
#######################################################################
    SUBMIT = 'Send Feedback'
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            form = FeedbackForm()
            
            frompage = flask.request.args.get('next',None)
            if frompage:
                params = {'next':frompage}
                actionurl = '{}?{}'.format(flask.url_for('feedback'),urllib.parse.urlencode(params))
            else:
                actionurl = flask.url_for('feedback')
                
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('feedback.html',thispagename='Send Feedback',form=form,action=GetFeedback.SUBMIT,
                                         actionurl=actionurl,
                                         inhibitseries=True,inhibityear=True,addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            form = FeedbackForm()

            # handle Cancel
            if request.form['whichbutton'] == GetFeedback.SUBMIT:
                
                fromaddr = form.fromemail.data
                toaddrs = ['scoretility@pobox.com']
                subject = '[scoretility feedback] v={}: {}'.format(version.__version__,form.subject.data)
                msg = 'From: {}\nTo: {}\nSubject: {}\n\n{}'.format(fromaddr, ', '.join(toaddrs), subject, form.message.data)
                
                # this doesn't work in development environment
                if not app.debug:
                    mailer = smtplib.SMTP('localhost')
                    mailer.sendmail(fromaddr,toaddrs,msg)
                    mailer.quit()
                    flask.flash('feedback sent successfully')
                else:
                    flask.flash('feedback sent successfully, message = \n{}'.format(msg))
                
            # commit database updates and close transaction
            db.session.commit()
            return (flask.redirect(flask.request.args.get('next')) or flask.url_for('index'))
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

#----------------------------------------------------------------------
app.add_url_rule('/feedback/',view_func=GetFeedback.as_view('feedback'),methods=['GET','POST'])
#----------------------------------------------------------------------

