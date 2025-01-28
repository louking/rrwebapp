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
from flask import jsonify, request, current_app
from flask.views import MethodView

# homegrown
from . import app
from .request_helpers import crossdomain
from .model import db, Club   # this is ok because this module only runs under flask
from .helpers import getagfactors

from loutilities.agegrade import AgeGrade

class parameterError(Exception): pass

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
            gender = request.args.get('gender',None)        # M, F, or X
            distance = request.args.get('distance',None)    # in miles
            timestr = request.args.get('time',None)         # in seconds or time string
            debug = request.args.get('debug', None)         # true for logger debug output

            output_result = {}

            # for backwards compatibility, use defaults if surface and club are not specified
            surface = request.args.get('surface', None)
            clubname = request.args.get('club', 'fsrcrt')   # FSRC Racing Team is only club to use this api
            club = Club.query.filter_by(shname=clubname).one()
            
            # create agfactors datastructure based on club's agegradetable
            if club.agegradetable:
                DEBUG = current_app.logger.debug if debug else None
                ag = AgeGrade(agegradedata=getagfactors(club.agegradetable), DEBUG=DEBUG)
            else:
                raise parameterError('club {clubname} has no age grade table configured')
            
            errorfield = 'age'
            age = int(age)
            errorfield = 'distance'
            distance = float(distance)
            errorfield = 'gender'
            if gender not in ['M', 'F', 'X']: raise ValueError('gender must be one of M, F, X')

            errorfield = 'time'
            timelist = timestr.split(':')
            time = 0.0
            for tval in timelist:
                time = time*60 + float(tval)

            errorfield = 'agegrade'
            agpercent, agtime, agfactor = ag.agegrade(age, gender, distance, time, surface=surface)

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
