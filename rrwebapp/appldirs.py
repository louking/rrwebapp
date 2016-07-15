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

# pypi
import appdirs

# store temporary uploads here
UPLOAD_TEMP_DIR = appdirs.user_data_dir( 'scoretility' )
if not os.path.exists( UPLOAD_TEMP_DIR ):
    os.makedirs( UPLOAD_TEMP_DIR, S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR )
