###########################################################################################
# forms - forms for rrwebapp
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/15/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################
'''
forms - forms for rrwebapp
===============================
'''
from flask_wtf import FlaskForm as Form
from wtforms import HiddenField, SelectField, StringField, IntegerField
from wtforms import FloatField, BooleanField, TextAreaField, validators
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
    # orderby field values must match field names in raceresult table
    orderby = SelectField('Order By',coerce=str,choices=[('agtime','agtime'),('agpercent','agpercent'),('time','time'),('overallplace','overallplace')])
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
    name = StringField('Name',[validators.Optional()])
    dateofbirth = StringField('Date of Birth',[validators.Optional()])
    gender = StringField('Gender',[validators.Optional()])
    hometown = StringField('Hometown',[validators.Optional()])
    renewdate = StringField('Renewal Date',[validators.Optional()])
    expdate = StringField('Expiration Date',[validators.Optional()])
    member = BooleanField('Is Member',[validators.Optional()])
    
########################################################################
class SeriesResultForm(Form):
########################################################################
    series = StringField('Series',[validators.Optional()])
    place = IntegerField('Gen Place',[validators.Optional()])
    name = StringField('Name',[validators.Optional()])
    gender = StringField('Gen',[validators.Optional()])
    agage = IntegerField('Age',[validators.Optional()])
    division = StringField('Div',[validators.Optional()])
    divisionlow = IntegerField('Div Lo',[validators.Optional()])
    divisionhigh = IntegerField('Div Hi',[validators.Optional()])
    divisionplace = IntegerField('Div Place',[validators.Optional()])
    club = StringField('Club',[validators.Optional()])
    time = StringField('Time',[validators.Optional()])
    pace = StringField('Pace',[validators.Optional()])
    agtime = StringField('AG Time',[validators.Optional()])
    agpercent = FloatField('AG %age',[validators.Optional()])

########################################################################
class RunnerResultForm(Form):
########################################################################
    name = StringField('Name',[validators.Optional()])
    series = StringField('Series',[validators.Optional()])
    date = StringField('Date',[validators.Optional()])
    distance = FloatField('Miles',[validators.Optional()])
    race = StringField('Race',[validators.Optional()])
    place = IntegerField('Gen Place',[validators.Optional()])
    gender = StringField('Gen',[validators.Optional()])
    agage = IntegerField('Age',[validators.Optional()])
    division = StringField('Div',[validators.Optional()])
    divisionplace = IntegerField('Div Place',[validators.Optional()])
    time = StringField('Time',[validators.Optional()])
    pace = StringField('Pace',[validators.Optional()])
    agtime = StringField('AG Time',[validators.Optional()])
    agpercent = FloatField('AG %age',[validators.Optional()])

########################################################################
class StandingsForm(Form):
########################################################################
    # TODO: is this even used?
    filterseries = SelectField('Series',coerce=str)
    filtergender = SelectField('Gender',coerce=str)
    filterdivision = SelectField('Division',coerce=str)
    racenum = IntegerField('Race Num')
    racename = StringField('Race Name')
    runner = StringField('Name')
    gender = StringField('Gender')
    age = IntegerField('Age')
    points = FloatField('Points')
    total = FloatField('Total')
    
########################################################################
class ChooseStandingsForm(Form):
########################################################################
    club = SelectField('Club',[validators.Optional()])
    year = SelectField('Year',[validators.Optional()],coerce=int)
    series = SelectField('Series',[validators.Optional()])
    
########################################################################
class ExportResultsForm(Form):
########################################################################
    start = StringField('Start Date',[validators.Optional()])
    end = StringField('End Date',[validators.Optional()])
    

