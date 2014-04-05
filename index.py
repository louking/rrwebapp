###########################################################################################
# index - just some boilerplate
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/04/14        Lou King        Create
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

# standard
import smtplib

# pypi
import flask
from flask import make_response,request
from flask.views import MethodView

# home grown
from . import app
from database_flask import db   # this is ok because this module only runs under flask

# module specific needs
from forms import FeedbackForm

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
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('feedback.html',thispagename='Send Feedback',form=form,action=GetFeedback.SUBMIT,
                                         addfooter=True)
        
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
                toaddrs = ['scoreit@foobox.com']
                subject = '[scoreit feedback] ' + form.subject.data
                msg = 'From: {}\nTo: {}\nSubject: {}\n\n{}'.format(fromaddr, ', '.join(toaddrs), subject, form.message.data)
                
                mailer = smtplib.SMTP('localhost')
                mailer.set_debuglevel(1)
                mailer.sendmail(fromaddr,toaddrs,msg)
                mailer.quit()
                
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

