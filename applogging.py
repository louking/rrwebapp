#!/usr/bin/python
###########################################################################################
# applogging - define logging for the application
#
#	Date		Author		Reason
#	----		------		------
#       01/11/14        Lou King        Create
#
#   Copyright 2014 Lou King
###########################################################################################
'''
applogging - define logging for the application
================================================
'''
# standard

# pypi

# module specific needs
from app import app

#----------------------------------------------------------------------
def setlogging():
#----------------------------------------------------------------------

    # TODO: move this to new module logging, bring in from dispatcher
    # set up logging
    ADMINS = ['lking@pobox.com']
    if not app.debug:
        from logging.handlers import SMTPHandler
        from logging import FileHandler, Formatter
        mail_handler = SMTPHandler('localhost',
                                   'noreply@steeplechasers.org',
                                   ADMINS, '[scoretility] exception encountered')
        if 'LOGGING_LEVEL_MAIL' in app.config:
            mailloglevel = app.config['LOGGING_LEVEL_MAIL']
        else:
            mailloglevel = logging.ERROR
        mail_handler.setLevel(mailloglevel)
        mail_handler.setFormatter(Formatter('''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s
        
        Message:
        
        %(message)s
        '''))
        app.logger.addHandler(mail_handler)
        
        logpath = None
        if 'LOGGING_PATH' in app.config:
            logpath = app.config['LOGGING_PATH']
            
        if logpath:
            file_handler = FileHandler(logpath,delay=True)
            if 'LOGGING_LEVEL_FILE' in app.config:
                fileloglevel = app.config['LOGGING_LEVEL_FILE']
            else:
                fileloglevel = logging.WARNING
            file_handler.setLevel(fileloglevel)
            app.logger.addHandler(file_handler)
        
            file_handler.setFormatter(Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
    
