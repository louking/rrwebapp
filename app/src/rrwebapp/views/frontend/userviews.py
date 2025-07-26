"""
userviews - frontend views which don't require login
=======================================================
"""
# standard
import traceback

# pypi
import flask
from flask import request, url_for, current_app
from flask.views import MethodView
import loutilities.renderrun as render

# home grown
from . import bp
from ...model import SERIES_OPTION_DISPLAY_CLUB, db
from ...model import Runner, RaceResult, Race, Series, RaceSeries, Club
from ...forms import SeriesResultForm, StandingsForm
from ...renderstandings import HtmlStandingsHandler, StandingsRenderer, addstyle
from ...apicommon import failure_response, success_response
from ...resultsutils import clubaffiliationelement

# admin guide
from ...version import __docversion__
adminguide = f'https://docs.scoretility.com/en/{__docversion__}/scoring-user-reference.html'

#################################
# seriesresults endpoint
#################################

class SeriesResults(MethodView):

    def get(self,raceid):
        try:
            seriesarg = request.args.get('series','')
            division = request.args.get('div','')
            gender = request.args.get('gen','')
            printerarg = request.args.get('printerfriendly','false')
            printerfriendly = (printerarg == 'true')

            form = SeriesResultForm()
    
            # get race record
            race = Race.query.filter_by(id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                current_app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(url_for('manageraces'))
            
            # determine precision for rendered output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
            # get all the results, and the race record
            results = []
            for series in race.series:
                seriesid = series.id
                seriesresults = RaceResult.query.filter_by(raceid=raceid,seriesid=seriesid).order_by(series.orderby).all()
                # this is easier, code-wise, than using sqlalchemy desc() function
                if series.hightolow:
                    seriesresults.reverse()
                results += seriesresults
            
            # fix up the following:
            #   * time gets converted from seconds
            #   * determine member matching, set runnerid choices and initially selected choice
            #   * based on matching, set disposition
            displayresults = []
            for result in results:
                runner = Runner.query.filter_by(id=result.runnerid).first()
                thisname = runner.name
                series = Series.query.filter_by(id=result.seriesid).first()
                thisseries = series.name
                thistime = render.rendertime(result.time,timeprecision)
                thisagtime = render.rendertime(result.agtime,agtimeprecision)
                thispace = render.rendertime(result.time / race.distance, 0, useceiling=False)
                thisdiv = ''
                if not result.divisionlow and not result.divisionhigh:
                    thisdiv=''
                elif not result.divisionlow or result.divisionlow <= 1:
                    thisdiv = '{} and under'.format(result.divisionhigh)
                elif result.divisionhigh == 99 or not result.divisionhigh:
                    thisdiv = '{} and up'.format(result.divisionlow)
                else:
                    thisdiv = '{} - {}'.format(result.divisionlow,result.divisionhigh)

                clubaffiliation = clubaffiliationelement(result)
                if not clubaffiliation:
                    clubaffiliation = ''

                if result.genderplace:
                    thisplace = result.genderplace
                elif result.agtimeplace:
                    thisplace = result.agtimeplace
                else:
                    thisplace = None

                # order must match that which is expected within seriesresults.html
                displayresults.append((result,thisseries,thisplace,thisname,thistime,thisdiv,clubaffiliation,thisagtime,thispace))
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('seriesresults.html',form=form,race=race,resultsdata=displayresults,
                                         adminguide=adminguide,
                                         series=seriesarg,division=division,gender=gender,printerfriendly=printerfriendly,
                                         inhibityear=True,inhibitclub=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/seriesresults/<int:raceid>',view_func=SeriesResults.as_view('seriesresults'),methods=['GET'])


#################################
# standings endpoint
#################################

class ViewStandings(MethodView):

    def get(self):
        try:
            club = request.args.get('club')
            year = request.args.get('year')
            series = request.args.get('series')
            description = request.args.get('desc')
            division = request.args.get('div','Overall')
            gender = request.args.get('gen','')
            printerarg = request.args.get('printerfriendly','false')
            printerfriendly = (printerarg == 'true')

            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                current_app.logger.error(cause)
                return flask.redirect(flask.url_for('frontend.index'))
            
            club_id = thisclub.id
            clubname = thisclub.name
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for '{}' club".format(series,clubname)
                flask.flash(cause)
                current_app.logger.error(cause)
                return flask.redirect(flask.url_for('frontend.index'))
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            thequery = Race.query.join(RaceSeries).join(Series).filter(Series.id==seriesid,Series.active==True).order_by(Race.date)
            races = thequery.all()
            racenums = list(range(1,len(races)+1))
            resulturls = [flask.url_for('.seriesresults',raceid=r.id) for r in races]
            
            # number of rows is set based on whether len(races) is even or odd
            numcols = 2
            even = len(races) // numcols == len(races) / (numcols*1.0)
            numrows = len(races) // numcols if even else len(races) // numcols + 1
            
            racerows = []
            racenum = {}
            for rownum in range(numrows):
                thisrow = []
                for col in range(numcols):
                    racenum[col] = rownum + numrows*col + 1
                    if racenum[col] in racenums:
                        rndx = racenum[col]-1
                        thisrow.append({'num':racenum[col],
                                        'resultsurl':resulturls[rndx],
                                        'race':'{} ({})'.format(races[rndx].name,races[rndx].date)})
                    else:
                        racenum[col] = None
                        thisrow.append({'num':None,'resultsurl':'','race':''})
                racerows.append(thisrow)
                
            # prepare to collect all the results for this series which have any results
            rr = StandingsRenderer(club_id,thisyear,thisseries,races,racenums)
                
            # declare "file" handler for HTML file type
            fh = HtmlStandingsHandler(racenums)
            rr.renderseries(fh)

            roworder = ['division','place','name','gender','age'] 
            if thisseries.has_series_option(SERIES_OPTION_DISPLAY_CLUB):
                roworder += ['clubs']
            roworder += ['nraces'] + ['race{}'.format(r) for r in racenums] + ['total']
            headerclasses = ['_rrwebapp-class-col-{}'.format(h) for h in ['division','place','name','gender','age']]
            if thisseries.has_series_option(SERIES_OPTION_DISPLAY_CLUB):
                headerclasses += ['_rrwebapp-class-col-{}'.format(h) for h in ['clubs']]
            headerclasses += ['_rrwebapp-class-col-{}'.format(h) for h in ['nraces']]
            headerclasses += ['_rrwebapp-class-col-race' for h in racenums]
            headerclasses += ['_rrwebapp-class-col-total']
            tooltips = [None,None,None,None,None] 
            if thisseries.has_series_option(SERIES_OPTION_DISPLAY_CLUB):
                tooltips += [None]
            tooltips += ['Number of races']
            tooltips += [r.name for r in races]
            tooltips += [None]
            
            # collect standings
            standings = []
            firstheader = True
            for gen in ['F', 'M', 'X']:
                rows = fh.iter(gen)
                for row in rows:
                    row['gender'] = addstyle(row['header'],gen,'gender')
                    #row['name'] = '<a href="{}?{}">{}</a>'.format(flask.url_for('runnerresults'),urllib.urlencode({'name':row['name'],'series':thisseries.name}),row['name'])
                    if row['header']:
                        row['gender'] = addstyle(row['header'],'Gen','gender')
                        if firstheader:
                            headings = [row[k] for k in roworder]
                            firstheader = False
                        else:
                            continue    # skip extra headers in dataset
                    else:
                        standings.append({'_class': row['_class'], 'data': [row[k] for k in roworder]})

            # headings, headerclasses, tooltips are used together
            headingdata = list(zip(headings,headerclasses,tooltips))
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headingdata=headingdata,
                                         adminguide=adminguide,
                                         racerows=racerows,standings=standings,description=description,
                                         displayclub=thisseries.has_series_option(SERIES_OPTION_DISPLAY_CLUB),
                                         division=division,gender=gender,printerfriendly=printerfriendly,
                                         inhibityear=True,inhibitclub=True)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            current_app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('frontend.index'))

bp.add_url_rule('/viewstandings/',view_func=ViewStandings.as_view('viewstandings'),methods=['GET'])


class AjaxGetSeries(MethodView):
    
    def post(self):
        try:
            clubsh = request.args.get('club',None)
            year = request.args.get('year',None)
            
            if not clubsh or not year:
                db.session.rollback()
                cause = 'Unexpected Error: both club and year must be specified'
                # this can happen if user has no cookie initialized when the popup is initially brought up
                # current_app.logger.error(cause)
                return failure_response(cause=cause)
                
            club = Club.query.filter_by(shname=clubsh).first()
            if not club:
                db.session.rollback()
                cause = 'Unexpected Error: club {} does not exist'.format(clubsh)
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            club_id = club.id
            
            allseries = Series.query.filter_by(active=True,club_id=club_id,year=year).all()
            # see https://editor.datatables.net/plug-ins/field-type/editor.select2
            theseseries = sorted([{'label':s.name, 'value':s.name} for s in allseries], key=lambda s: s['label'])
            # choices = [{'label':'Select Series', 'value':''}] + theseseries
            choices = theseseries

            # commit database updates and close transaction
            db.session.commit()
            return success_response(choices=choices)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            current_app.logger.error(cause)
            return failure_response(cause=cause)

bp.add_url_rule('/standings/_getseries',view_func=AjaxGetSeries.as_view('standings/_getseries'),methods=['POST'])


class AjaxGetYears(MethodView):
    
    def post(self):
        try:
            clubsh = request.args.get('club',None)
            
            if not clubsh:
                db.session.rollback()
                cause = 'Unexpected Error: both club and year must be specified'
                current_app.logger.error(cause)
                return failure_response(cause=cause)
                
            club = Club.query.filter_by(shname=clubsh).first()
            if not club:
                db.session.rollback()
                cause = 'Unexpected Error: club {} does not exist'.format(clubsh)
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            club_id = club.id
            
            allseries = Series.query.filter_by(active=True,club_id=club_id).all()

            years = []
            for thisseries in allseries:
                if thisseries.year not in years:
                    years.append(thisseries.year)
            years.sort()
            theseyears = [(y,y) for y in years]

            choices = [(0,'Select Year')] + theseyears

            # commit database updates and close transaction
            db.session.commit()
            return success_response(choices=choices)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            current_app.logger.error(cause)
            return failure_response(cause=cause)

bp.add_url_rule('/standings/_getyears',view_func=AjaxGetYears.as_view('standings/_getyears'),methods=['POST'])

