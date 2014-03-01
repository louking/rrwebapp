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
from wtforms import HiddenField, SelectField, StringField, IntegerField, BooleanField, validators
from wtforms import SelectMultipleField, widgets

########################################################################
class MultiCheckboxField(SelectMultipleField):
########################################################################
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

########################################################################
class UserForm(Form):
########################################################################
    email = StringField('Email')
    name = StringField('Name')
    password = StringField('Password',[validators.Optional()])
    hidden_userid = HiddenField('',[validators.Optional()])
    owner = BooleanField('Owner',[validators.Optional()])
    club = SelectField('Club',[validators.Optional()],coerce=int)
    admin = BooleanField('Admin',[validators.Optional()])
    viewer = BooleanField('Viewer',[validators.Optional()])
    
########################################################################
class UserSettingsForm(Form):
########################################################################
    email = StringField('Email')
    name = StringField('Name')
    password = StringField('Password',[validators.Optional()])
    hidden_userid = HiddenField('',[validators.Optional()])
    
########################################################################
class RaceForm(Form):
########################################################################
    filterseries = SelectField('FilterSeries',coerce=str)
    date = StringField('Date')
    distance = StringField('Distance')
    surface = SelectField('Surface',choices=[('road','road'),('track','track'),('trail','trail')])
    name = StringField('Name')
    results = StringField('Results')
    
########################################################################
class RaceSettingsForm(Form):
########################################################################
    name = StringField('Name')
    date = StringField('Date')
    distance = StringField('Miles')
    surface = SelectField('Surface',coerce=str)
    racenum = IntegerField('Race Num')
    series = MultiCheckboxField("Series", coerce=int)

########################################################################
class SeriesForm(Form):
########################################################################
    copyyear = SelectField('Copy from Year',[validators.Optional()],choices=[])
    name = StringField('Series Name')
    maxraces = IntegerField('Max Races',[validators.Optional()])
    multiplier = IntegerField('Multiplier',[validators.Optional()])
    maxgenpoints = IntegerField('Max Gender Points',[validators.Optional()])
    maxdivpoints = IntegerField('Max Division Points',[validators.Optional()])
    maxbynumrunners = BooleanField('Max by Number of Runners')
    orderby = SelectField('Order By',coerce=str,choices=[('agtime','agtime'),('agpercent','agpercent'),('time','time')])
    hightolow = SelectField('Order',coerce=int,choices=[(0,'ascending'),(1,'descending')])
    membersonly = BooleanField('Members Only')
    averagetie = BooleanField('Average Ties')
    calcoverall = BooleanField('Calculate Overall')
    calcdivisions = BooleanField('Calculate Divisions')
    calcagegrade = BooleanField('Calculate Age Grade')
    races = MultiCheckboxField("Races", coerce=int)
    
########################################################################
class DivisionForm(Form):
########################################################################
    copyyear = SelectField('Copy from Year',[validators.Optional()],choices=[])
    seriesid = SelectField('Series',coerce=int)
    divisionlow = IntegerField('From Age',[validators.Optional()])
    divisionhigh = IntegerField('To Age',[validators.Optional()])

########################################################################
class MemberForm(Form):
########################################################################
    filtermember = StringField('Search')
    name = StringField('Name')
    dateofbirth = StringField('Date of Birth')
    gender = StringField('Gender')
    hometown = StringField('Hometown')
    renewdate = StringField('Renew Date')
    member = BooleanField('Is Member')
    
