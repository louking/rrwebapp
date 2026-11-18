'''
resultsfilter - reduce a large results file to rows which may match club members
==================================================================================

Large races (e.g., Marine Corps Marathon, ~25,000 finishers) are impractical to import
in full. This module reads such a file, keeps only rows which Import would give a
disposition (the Match column on Edit Participants), and writes a csv file in the format
expected by :class:`raceresults.RaceResults` (i.e., Import on Edit Participants).

The disposition comes from :meth:`resultsutils.ImportResults.set_initialdisposition`, so the
filter keeps exactly the rows Import would show with a non-empty Match.

The input file may have an age group / division column instead of age. Each row is checked
at the ages in its age group that could give a match, and the output age is the one which
gives the best disposition.

Kept deliberately free of view/celery imports so it can be tested with the bare Flask fixture.
'''

# standard
import csv
import re
from datetime import time as datetime_time, timedelta

# pypi
from loutilities import textreader
from loutilities.timeu import age as ageasof, asctime

# home grown
from .resultsutils import ImportResults, Record, normname
from .resultsutils import DISP_MATCH, DISP_CLOSE, DISP_CLOSEAGE, DISP_MISSED, DISP_NOTUSED

class headerError(Exception): pass

tYmd = asctime('%Y-%m-%d')

# input header recognition. Keys are generic fields, values are possible header cells
# (lower case, single spaces) in priority order. This is a superset of raceresults.fieldxform
INFIELDS = {
    'place':     ['place', 'pl', 'overall place', 'gunplace', 'overall'],
    'lastname':  ['last name', 'lastname', 'last'],
    'firstname': ['first name', 'firstname', 'first'],
    'name':      ['name', 'runner', 'full name'],
    'gender':    ['gender', 'sex', 'male/female', 's'],
    'age':       ['age'],
    'agegroup':  ['age group', 'agegroup', 'age division', 'division', 'div', 'category', 'ag'],
    'chiptime':  ['actual time', 'net time', 'nettime', 'chip time', 'chiptime'],
    'time':      ['time'],
    'guntime':   ['gun time', 'guntime', 'clock time', 'clocktime'],
    'city':      ['city'],
    'state':     ['state', 'st'],
    'hometown':  ['hometown'],
    'club':      ['club', 'team'],
}

# time fields, in the order raceresults.fieldxform prefers them. All time columns found in the
# input are written to the output, so the admin can delete or rename a column to have Import use
# another time. Import uses the first of these which is present, e.g., chip time over gun time
TIMEFIELDS = ['chiptime', 'time', 'guntime']

# output headers must be recognized by raceresults.fieldxform; the last two are informational
# and are ignored by RaceResults because they don't match any of its header possibilities
OUTFIELDS = ['place', 'name', 'gender', 'age'] + TIMEFIELDS + ['city', 'state', 'hometown', 'club']
OUT_AGEGROUP = 'age group'
OUT_NOTE = 'filter note'

# upper bound used for open ended age groups like 80+
MAXAGE = 150

def _normcell(cell):
    '''normalize a header cell for comparison'''
    if cell is None:
        return ''
    return ' '.join(str(cell).lower().split())

def findheader(row):
    '''
    determine column indexes for the generic fields, if row looks like a header

    :param row: list of cells
    :rtype: {field: column index, ...} or None if this isn't a header row
    '''
    cells = [_normcell(c) for c in row]
    cols = {}
    used = set()
    for field, options in INFIELDS.items():
        for option in options:
            if option in cells:
                ndx = cells.index(option)
                if ndx not in used:
                    cols[field] = ndx
                    used.add(ndx)
                    break

    hasname = 'name' in cols or ('firstname' in cols and 'lastname' in cols)
    hasage = 'age' in cols or 'agegroup' in cols
    hastime = any(f in cols for f in TIMEFIELDS)
    if hasname and hasage and 'place' in cols and hastime:
        # prefer separate first/last name over single name column if both present
        if 'firstname' in cols and 'lastname' in cols:
            cols.pop('name', None)
        return cols
    return None

GENDER_PREFIX = re.compile(r'^\s*([mfx])(?=[\s\d-]|$)', re.IGNORECASE)
RANGE = re.compile(r'(\d{1,3})\s*(?:-|to|thru|through)\s*(\d{1,3})', re.IGNORECASE)
COMPACT_RANGE = re.compile(r'^\s*[a-z]*\s*(\d{2})(\d{2})\s*$', re.IGNORECASE)
OVER = re.compile(r'(\d{1,3})\s*(?:\+|(?:&|and)?\s*(?:over|older|up)\b)', re.IGNORECASE)
UNDER_AFTER = re.compile(r'(\d{1,3})\s*(?:&|and)?\s*(?:under|younger)\b', re.IGNORECASE)
UNDER_BEFORE = re.compile(r'(?:under|<)\s*(\d{1,3})', re.IGNORECASE)
BARE_AGE = re.compile(r'^\s*(\d{1,3})(?:\.0+)?\s*$')

def parseagegroup(value):
    '''
    interpret an age group / division value

    handles, e.g., '35 to 39', '35-39', 'M35-39', 'F 40 - 44', 'M4044', '80+', '80 & Over',
    '19 & Under', 'Under 20', or a bare age

    :param value: cell value from the file
    :rtype: (low, high, gender) -- low/high are None if unknown; gender is 'M', 'F', 'X' or None
    '''
    if value is None:
        return None, None, None
    if isinstance(value, (int, float)):
        return int(value), int(value), None

    text = str(value).strip()
    if not text:
        return None, None, None

    gender = None
    m = GENDER_PREFIX.match(text)
    if m:
        gender = m.group(1).upper()

    m = RANGE.search(text)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        if low <= high:
            return low, high, gender

    m = COMPACT_RANGE.match(text)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        if low < high:
            return low, high, gender

    m = OVER.search(text)
    if m:
        return int(m.group(1)), MAXAGE, gender

    m = UNDER_AFTER.search(text)
    if m:
        return 0, int(m.group(1)), gender

    m = UNDER_BEFORE.search(text)
    if m:
        return 0, int(m.group(1)) - 1, gender

    m = BARE_AGE.match(text)
    if m:
        return int(m.group(1)), int(m.group(1)), gender

    return None, None, gender

def rendertime(value):
    '''
    render time cell as string which raceresults.normalizeracetime will accept

    :param value: str, datetime.time, timedelta, or float/int days (excel)
    :rtype: string, '' if empty
    '''
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, datetime_time):
        secs = value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1000000
    elif isinstance(value, timedelta):
        secs = value.total_seconds()
    elif isinstance(value, (int, float)):
        secs = value * 24 * 60 * 60
    else:
        return str(value)

    # avoid quantization error through excel
    secs = round(secs * 1000) / 1000.0
    hours = int(secs // 3600)
    minutes = int((secs - hours * 3600) // 60)
    seconds = secs - hours * 3600 - minutes * 60
    return f'{hours}:{minutes:02d}:{seconds:06.3f}'

def renderplace(value):
    '''return place as int string, or '' if not a number'''
    if value is None:
        return ''
    try:
        return str(int(float(str(value).strip())))
    except ValueError:
        return ''

def _cell(row, cols, field):
    ndx = cols.get(field)
    if ndx is None or ndx >= len(row):
        return None
    return row[ndx]

def _str(value):
    return '' if value is None else str(value).strip()

def _memberage(member, racedate_dt):
    '''return member's age on race date, or None if no valid dob'''
    try:
        return ageasof(racedate_dt, tYmd.asc2dt(member['dob']))
    except (ValueError, TypeError, KeyError):
        return None

# best first. DISP_NOTUSED ('') is what Edit Participants shows as an empty Match column
DISP_RANK = [DISP_MATCH, DISP_CLOSE, DISP_CLOSEAGE, DISP_MISSED]

def candidateages(pool, name, racedate_dt):
    '''
    ages on the race date of all pool members whose name is similar to this name, using the
    same name matching as clubmember.ClubMember.findmember()

    :param pool: clubmember.ClubMember instance
    :param name: name from results
    :param racedate_dt: race date, datetime
    :rtype: (namematched, ages) -- namematched is False if no similar name; ages is a sorted list
    '''
    matches = pool.getmember(name)
    if not matches:
        return False, []
    ages = set()
    for checkmember in [matches['matchingmembers'][0]['name']] + matches['closematches']:
        for member in pool.getmember(checkmember)['matchingmembers']:
            memberage = _memberage(member, racedate_dt)
            if memberage is not None:
                ages.add(memberage)
    return True, sorted(ages)

class ResultsFilter():
    '''
    filter a results file to rows which Import would give a disposition

    :param filename: results file (csv, xls, xlsx)
    :param importer: resultsutils.ImportResults instance for the race, or None to only check the header
    '''

    def __init__(self, filename, importer=None):
        self.filename = filename
        self.importer = importer
        if importer:
            self.racedate_dt = tYmd.asc2dt(importer.race.date)

        self.file = textreader.TextReader(filename)
        if not self.file.getdelimited():
            self.file.close()
            raise headerError(f'{filename}: only delimited files (csv, xls, xlsx) can be filtered')

        # find header row
        self.cols = None
        try:
            while not self.cols:
                self.cols = findheader(next(self.file))
        except StopIteration:
            self.file.close()
            raise headerError(f'{filename}: header not found. Header needs place, name (or first and last name), '
                              f'time, and age or age group columns')

        # remember which optional output fields are present in the input
        self.outfields = [f for f in OUTFIELDS if f in self.cols or f in ['place', 'name', 'gender', 'age']]
        self.timefields = [f for f in TIMEFIELDS if f in self.cols]
        self.fieldnames = self.outfields + [OUT_AGEGROUP, OUT_NOTE]

    def disposition(self, name, resultage):
        '''
        determine the disposition Import would give this result

        :param name: normalized result name
        :param resultage: result age, 0 if unknown
        :rtype: initialdisposition
        '''
        # plain object standing in for the ManagedResult Import would create
        result = Record()
        result.name = name
        result.age = resultage
        result.runnerid = None
        self.importer.dbresult = result
        return self.importer.set_initialdisposition({})

    def bestdisposition(self, name, low, high):
        '''
        find the result age within [low, high] which gives the best disposition

        Import gives a better disposition when the result age equals or is near a member's age,
        so the ages tried are each name-matched member's age clamped to the range, and the
        range's low end. If the range is unknown, the members' ages are tried as is.

        :param name: normalized result name
        :param low: low end of age range, or None if unknown
        :param high: high end of age range, or None if unknown
        :rtype: (disposition, age) -- age is 0 if unknown
        '''
        namematched, ages = candidateages(self.importer.pool, name, self.racedate_dt)
        if low is None:
            tryages = ages or [0]
        else:
            tryages = sorted({low} | {min(max(a, low), high) for a in ages})

        # without a similar name only the first age matters; the disposition doesn't depend on age
        if not namematched:
            tryages = tryages[:1]

        best = (DISP_NOTUSED, tryages[0])
        for tryage in tryages:
            disposition = self.disposition(name, tryage)
            if disposition in DISP_RANK and (best[0] not in DISP_RANK
                                             or DISP_RANK.index(disposition) < DISP_RANK.index(best[0])):
                best = (disposition, tryage)
                if disposition == DISP_MATCH:
                    break
        return best

    def close(self):
        self.file.close()

    def rows(self):
        '''
        generate input rows as dicts with generic keys, skipping rows that Import would skip or reject

        :rtype: generator of dict
        '''
        cols = self.cols
        while True:
            # TextReader has __next__ but not __iter__
            try:
                row = next(self.file)
            except StopIteration:
                return

            if 'firstname' in cols:
                name = ' '.join([_str(_cell(row, cols, 'firstname')), _str(_cell(row, cols, 'lastname'))]).strip()
            else:
                name = _str(_cell(row, cols, 'name'))

            # skip blank names or ones Import would reject (see raceresults.RaceResults.__next__)
            if not name or name[0] in '=-/!':
                continue

            # Import skips results with no time, using the first time column present
            times = {f: rendertime(_cell(row, cols, f)) for f in self.timefields}
            if not times[self.timefields[0]]:
                continue

            yield {
                'row': row,
                'name': name,
                'times': times,
            }

    def filter(self, outfilename, progress=None, progressevery=500):
        '''
        write rows which may match members to outfilename

        :param outfilename: output csv file name
        :param progress: optional function(rowsread) called periodically
        :param progressevery: number of rows between progress calls
        :rtype: dict with counts: read, kept, agefrommember (kept without age group in the file)
        '''
        cols = self.cols
        stats = {'read': 0, 'kept': 0, 'agefrommember': 0}
        with open(outfilename, 'w', newline='', encoding='utf8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=self.fieldnames)
            writer.writeheader()

            for inrow in self.rows():
                stats['read'] += 1
                if progress and stats['read'] % progressevery == 0:
                    progress(stats['read'])

                row = inrow['row']
                if 'age' in cols:
                    agegroup = _cell(row, cols, 'age')
                else:
                    agegroup = _cell(row, cols, 'agegroup')
                low, high, aggender = parseagegroup(agegroup)
                gender = _str(_cell(row, cols, 'gender')) or aggender or ''

                name = normname(inrow['name'])
                disposition, outage = self.bestdisposition(name, low, high)
                if disposition == DISP_NOTUSED:
                    continue

                note = disposition
                if low is None and outage:
                    stats['agefrommember'] += 1
                    note += '; age from member record, no age group in file'

                outrow = {
                    'place': renderplace(_cell(row, cols, 'place')),
                    'name': inrow['name'],
                    'gender': gender,
                    'age': outage or '',
                    OUT_AGEGROUP: _str(agegroup),
                    OUT_NOTE: note,
                }
                outrow.update(inrow['times'])
                for f in ['city', 'state', 'hometown', 'club']:
                    if f in self.outfields:
                        outrow[f] = _str(_cell(row, cols, f))

                writer.writerow(outrow)
                stats['kept'] += 1

        if progress:
            progress(stats['read'])
        return stats

    def count(self):
        '''
        count rows which will be considered by filter(). This consumes the file, so
        a new ResultsFilter is needed afterwards

        :rtype: int
        '''
        return sum(1 for _ in self.rows())
