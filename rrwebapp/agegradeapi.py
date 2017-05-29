###########################################################################################
# agegradeapi - agegrade api  for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       05/29/17        Lou King        Create
#
#   Copyright 2017 Lou King.  All rights reserved
#
###########################################################################################

# standard
from sys import exc_info

# pypi
from flask import jsonify, request
from flask.views import MethodView

# homegrown
from . import app
from request import crossdomain
from database_flask import db   # this is ok because this module only runs under flask

from loutilities.agegrade import AgeGrade
ag = AgeGrade()


#######################################################################
class AgeGradeApi(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    @crossdomain(origin='*')
    def get(self):
    #----------------------------------------------------------------------
        try:
            # agegrade(age,gender,distance,timestr)
            age = request.args.get('age',None)              # integer #years
            gender = request.args.get('gender',None)        # M or F
            distance = request.args.get('distance',None)    # in miles
            timestr = request.args.get('time',None)         # in seconds or time string

            output_result = {}

            errorfield = 'age'
            age = int(age)
            errorfield = 'distance'
            distance = float(distance)
            errorfield = 'gender'
            if gender not in ['M','F']: raise ValueError, 'gender must be one of M, F'

            errorfield = 'time'
            timelist = timestr.split(':')
            time = 0.0
            for tval in timelist:
                time = time*60 + float(tval)

            errorfield = 'agegrade'
            agpercent,agtime,agfactor = ag.agegrade(age,gender,distance,time)

            output_result['status'] = 'success'
            output_result['agpercent'] = agpercent
            output_result['agtime'] = agtime
            output_result['agfactor'] = agfactor

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            output_result['status'] = 'failure'
            output_result['message'] = 'invalid parameter'
            output_result['errorfield'] = errorfield
            exctype, excvalue, exctb = exc_info()
            output_result['details'] = '{}, {}'.format(exctype.__name__, excvalue)

            return jsonify(output_result)

#----------------------------------------------------------------------
app.add_url_rule('/_agegrade',view_func=AgeGradeApi.as_view('_agegrade'),methods=['GET'])
#----------------------------------------------------------------------
