###########################################################################################
# forms - forms for rrwebapp
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/15/14        Lou King        Create
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
forms - forms for rrwebapp
===============================
'''
from flask.ext.wtf import Form
from wtforms import SelectField, StringField

########################################################################
class RaceForm(Form):
########################################################################
    filterseries = SelectField('FilterSeries',coerce=str)
    date = StringField('Date')
    distance = StringField('Distance')
    surface = StringField('Surface')
    name = StringField('Name')
    results = StringField('Results')
    
########################################################################
class SeriesForm(Form):
########################################################################
    date = StringField('Date')
    distance = StringField('Distance')
    surface = StringField('Surface')
    name = StringField('Name')
    results = StringField('Results')
    
