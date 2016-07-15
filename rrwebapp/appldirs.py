###########################################################################################
#       Date            Author          Reason
#       ----            ------          ------
#       07/15/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
###########################################################################################

# standard
import os
import os.path
from stat import S_IRGRP, S_IRUSR, S_IWGRP, S_IWUSR

# homegrown
from . import app

class parameterError(Exception): pass

# store temporary uploads here
UPLOAD_TEMP_DIR = app.config.get('UPLOAD_TEMP_DIR','')
if not UPLOAD_TEMP_DIR:
    raise parameterError, 'rrwebapp.cfg [app] section requires UPLOAD_TEMP_DIR'

if not os.path.exists( UPLOAD_TEMP_DIR ):
    raise parameterError, "[app] UPLOAD_TEMP_DIR '{}' directory missing".format(UPLOAD_TEMP_DIR)
