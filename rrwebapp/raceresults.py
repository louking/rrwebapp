'''
raceresults  -- retrieve race results from a file
===================================================
'''

# standard
import os.path

# pypi

# github

# home grown
from . import app
from loutilities import textreader
from loutilities.timeu import racetimesecs

# fieldxform is a dict whose keys are the 'real' information we're interested in
# the value for a particular key contains a list with possible header entries which might be used to represent that key
# field used is prioritized by order in list
# TODO: get these from a configuration file
# IF THESE CHANGE, MUST CHANGE static/docs/importresults.csv
fieldxform = {
    'place':['place','pl','gunplace','overall place'],
    'lastname':[['last','name'],'last name','lastname','last'],
    'firstname':[['first','name'],'first name','firstname','first'],
    'name':['name','runner'],
    'gender':['gender','sex','male/female','s'],
    'age':['age','ag'],
    'time':['actual time','nettime','chiptime','time','guntime'],
    'city':['city'],
    'state':['state','st'],
    'hometown':['hometown'],
    'club':['club','team'],
}

# exceptions for this module.  See __init__.py for package exceptions
class headerError(Exception): pass
class dataError(Exception): pass

# for _normalizetime
PACE_FAST = 2.5 * 60.0  # 2:30/mile is pretty fast
PACE_SLOW = 30 * 60     # 30:00/mile is pretty slow

#----------------------------------------------------------------------
def normalizeracetime(racetime, distance, fastpace=PACE_FAST, slowpace=PACE_SLOW):
#----------------------------------------------------------------------
    '''
    normalize a race time in hh:mm:ss format

    :param racetime: hh:mm:ss or hh:mm or mm:ss or ss, all allowing decimal
    :param distance: distance in units (defaults assume miles)
    :param fastpace: fast pace in seconds per unit (default assumes seconds/mile)
    :param slowpace: slow pace in seconds per unit (default assumes seconds/mile)
    '''
    return racetimesecs(racetime, distance, fastpace, slowpace)
    
########################################################################
class RaceResults():
########################################################################
    '''
    get race results from a file
    
    :params filename: filename from which race results are to be retrieved
    :params distance: distance for race (miles)
    :params timereqd: default True, set to False if just looking at registration list
    '''
    #----------------------------------------------------------------------
    def __init__(self,filename,distance,timereqd=True):
    #----------------------------------------------------------------------
        # open the textreader using the file
        self.file = textreader.TextReader(filename)
        self.filename = filename
        self.distance = distance
        self.timereqd = timereqd
        
        # text file allows non-contiguous rows -- all others must be contiguous
        root,ext = os.path.splitext(filename)
        if ext == '.txt':
            self.contiguousrows = False
        else:
            self.contiguousrows = True
        
        # self.field item value will be of form {'begin':startindex,'end':startindex+length} for easy slicing
        self.field = {}

        # scan to the header line
        self._findhdr()

    #----------------------------------------------------------------------
    def _findhdr(self):
    #----------------------------------------------------------------------
        '''
        find the header in the file
        '''
    
        foundhdr = False
        delimited = self.file.getdelimited()
        fields = list(fieldxform.keys())
        REQDFIELDS = ['place', 'gender', 'age']    # 'name' fields handled separately
        if self.timereqd:
            REQDFIELDS.append('time')
        MINMATCHES = len(REQDFIELDS) + 1    # add one for 'name'

        # catch StopIteration, which means header wasn't found in the file
        try:
            # loop for each line until header found
            while True:
                origline = next(self.file)
                fieldsfound = 0
                self.field = {} # need to clear in case earlier line had some garbage
                line = []
                if not delimited:
                    for word in origline.split():
                        line.append(word.lower())
                else:
                    for word in origline:
                        line.append(str(word).lower())  # str() called in case non-string returned in origline
                    
                # loop for each potential self.field in a header
                for fieldndx in range(len(fields)):
                    f = fields[fieldndx]
                    match = fieldxform[f]
                    
                    # loop for each match possiblity, then within the fields in file header
                    # folding loop likes this gives precedence to the list order of the match possibilities
                    for m in match:
                        # loop for each column in this line, trying to find match possiblities
                        matchfound = False
                        for linendx in range(len(line)):                        
                            # match over the end of the line is no match
                            # m is either a string or a list of strings
                            if isinstance(m, str):
                                m = [m]         # make single string into list
                            if linendx+len(m)>len(line):
                                continue
                            # if we found the match, remember start and end of match
                            if line[linendx:linendx+len(m)] == m:
                                if f not in self.field: self.field[f] = {}
                                self.field[f]['start'] = linendx
                                self.field[f]['end'] = linendx + len(m)
                                self.field[f]['match'] = m
                                self.field[f]['genfield'] = f   # seems redundant, but [f] index is lost later in self.foundfields
                                fieldsfound += 1
                                matchfound = True
                                break   # match possibility loop
                        
                        # found match for this self.field
                        if matchfound: break
                
                # here we've gone through each self.field in the line
                # need to match more than MINMATCHES to call it a header line
                if fieldsfound >= MINMATCHES:
                    # special processing for name fields
                    if 'name' not in self.field and ('firstname' in self.field and 'lastname' in self.field):
                        self.splitnames = True
                    elif 'name' in self.field and ('firstname' in self.field and 'lastname' in self.field):
                        self.field.pop('name')  # redundant and wrong
                        self.splitnames = True
                    elif 'name' in self.field and ('lastname' in self.field and 'firstname' not in self.field):
                        namefield = self.field.pop('name')  # assume this was meant to be 'firstname'
                        self.field['firstname'] = namefield
                        self.splitnames = True
                    elif 'name' in self.field and ('lastname' not in self.field and 'firstname' in self.field):
                        raise headerError('{0}: inconsistent name fields found in header: {1}'.format(self.filename,origline))
                    elif 'name' in self.field:  # not 'lastname' or 'firstname'
                        self.splitnames = False
                    else:                       # insufficient name fields
                        raise headerError('{0}: no name fields found in header: {1}'.format(self.filename,origline))
                    
                    # verify that all other required fields are present
                    fieldsnotfound = []
                    for f in REQDFIELDS:
                        if f not in self.field:
                            fieldsnotfound.append(f)
                    if len(fieldsnotfound) != 0:
                        raise headerError('{0}: could not find fields {1} in header {2}'.format(self.filename,fieldsnotfound,origline))
                        
                    # sort found fields by order found within the line
                    foundfields_dec = sorted([(self.field[f]['start'],self.field[f]) for f in self.field])
                    self.foundfields = [ff[1] for ff in foundfields_dec] # get rid of sorting decorator
                        
                    # here we have decided it is a header line
                    # if the file is not delimited, we have to find where these fields start
                    # and tell self.file where the self.field breaks are
                    # assume multi self.field matches are separated by single space
                    if not delimited:
                        # sort found fields by 'start' linendx (self.field number within line)
                        # loop through characters in original line, skipping over spaces within matched fields, to determine
                        # where delimiters should be
                        delimiters = []
                        thischar = 0
                        foundfields_iter = iter(self.foundfields)
                        thisfield = next(foundfields_iter)
                        while True:
                            # scan past the white space
                            while thischar < len(origline) and origline[thischar] == ' ': thischar += 1
                            
                            # we're done looking if we're at the end of the line
                            if thischar == len(origline): break
                            
                            # found a word, remember where it was
                            delimiters.append(thischar)
                            
                            # look for the next match of known header fields
                            matchfound = False
                            if thisfield is not None:
                                # if a match, might be multiple words.  Probably ok to assume single space between them
                                fullmatch = ' '.join(thisfield['match'])
                                if origline[thischar:thischar+len(fullmatch)].lower() == fullmatch:
                                    thischar += len(fullmatch)
                                    matchfound = True
                                    try:
                                        thisfield = next(foundfields_iter)
                                    except StopIteration:
                                        thisfield = None
                            
                            # if found a match, thischar is already updated.  Otherwise, scan past this word
                            if not matchfound:
                                while thischar < len(origline) and origline[thischar] != ' ': thischar += 1
                            
                            # we're done looking if we're at the end of the line
                            if thischar == len(origline): break
                        
                        # set up delimiters in the file reader
                        app.logger.debug('delimiters found at {}'.format(delimiters))
                        self.file.setdelimiter(delimiters)
                                    
                    break

            # header fields are in foundfields
            # need to figure out the indeces for data which correspond to the foundfields
            self.fieldhdrs = []
            self.fieldcols = []
            skipped = 0
            for f in self.foundfields:
                self.fieldhdrs.append(f['genfield'])
                currcol = f['start'] - skipped
                self.fieldcols.append(currcol)
                skipped += len(f['match']) - 1  # if matched multiple columns, need to skip some
            app.logger.debug('found fieldhdrs {}'.format(self.fieldhdrs))
                
        # not good to come here
        except StopIteration:
            raise headerError('{0}: header not found'.format(self.filename))
        
    #----------------------------------------------------------------------
    def _normalizetime(self,time,distance):
    #----------------------------------------------------------------------
        '''
        normalize the time field, based on distance
        
        :param time: time field from original file
        :param distance: distance of the race, for normalizedtimetype analysis
        
        :rtype: float time (seconds)
        '''
        
        # if string, assume hh:mm:ss or mm:ss or ss
        if type(time) in [str,str]:
            thistime = time
    
        # if float or int, assume it came from excel, and is in days
        elif type(time) in [float,int]:
            tottime = time * (24*60*60.0)
            
            # to avoid quantization error through excel, round with epsilon of 0.00005
            tottime = round(tottime*10000)/10000.0
            hours = int(tottime/3600)
            tottime -= hours*3600
            minutes = int(tottime/60)
            tottime -= minutes*60
            seconds = tottime
            thistime = '{}:{}:{}'.format(hours, minutes, seconds)
        
        return normalizeracetime(thistime, distance)
    
    #----------------------------------------------------------------------
    def __next__(self):
    #----------------------------------------------------------------------
        '''
        return dict with generic headers and associated data from file
        '''
        
        # get next raw line from the file
        # TODO: skip lines which empty text or otherwise invalid lines
        textfound = False
        while not textfound:
            rawline = next(self.file)
            textfound = True    # hope for the best
            
            # pick columns which are associated with generic headers
            filteredline = [rawline[i] for i in range(len(rawline)) if i in self.fieldcols]
            
            # create dict association, similar to csv.DictReader
            result = dict(list(zip(self.fieldhdrs,filteredline)))
            
            # special processing if name is split, to combine first, last names
            if self.splitnames:
                first = result.pop('firstname').strip()
                last = result.pop('lastname').strip()
                result['name'] = ' '.join([first,last])
                
            # special processing for age - normalize to integer
            if 'age' in result and result['age'] is not None:
                if type(result['age']) in [str,str]:
                    result['age'] = result['age'].strip()
                if not result['age']: # 0 or ''
                    result['age'] = None
                else:
                    try:
                        result['age'] = int(result['age'])
                    except ValueError:
                        if not self.contiguousrows:
                            textfound = False
                            continue
                        else:
                            raise dataError("invalid age '{}' for record with name '{}'".format(result['age'],result['name']))
                
            # special processing for place - normalize to integer
            if 'place' in result and result['place'] is not None:
                if type(result['place']) in [str,str]:
                    result['place'] = result['place'].strip()
                if not result['place']:  # 0 or ''
                    result['place'] = None
                else:
                    try:
                        result['place'] = int(result['place'])
                    except ValueError:
                        if not self.contiguousrows:
                            textfound = False
                            continue
                        else:
                            raise dataError("invalid place '{}' for record with name '{}'".format(result['place'],result['name']))
                
            # look for some obvious errors in name
            if result['name'] is None or result['name'][0] in '=-/!':
                if not self.contiguousrows:
                    textfound = False
                    continue
                else:
                    raise dataError("invalid name '{}'".format(result['name']))
            
            # TODO: add normalization for gender
            
            # add normalization for race time (e.g., convert hours to minutes if misuse of excel)
            if 'time' in result:
                result['time'] = self._normalizetime(result['time'],self.distance)
        
        # and return result
        return result
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close the file
        '''
        self.file.close()
        
