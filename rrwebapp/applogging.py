'''
applogging - define logging for the application
================================================
'''
# pypi

# home grown -- done here for backwards compatility testing
from loutilities.user.applogging import setlogging

# #----------------------------------------------------------------------
# def setlogging():
# #----------------------------------------------------------------------
#     # need to wait until app created to import
#     from . import app

#     # this is needed for any INFO or DEBUG logging
#     app.logger.setLevel(logging.DEBUG)

#     # patch werkzeug logging -- not sure why this is being bypassed in werkzeug._internal._log
#     werkzeug_logger = logging.getLogger('werkzeug')
#     werkzeug_logger.setLevel(logging.INFO)

#     # TODO: move this to new module logging, bring in from dispatcher
#     # set up logging
#     ADMINS = ['lking@pobox.com']
#     if not app.debug:
#         mail_handler = SMTPHandler('localhost',
#                                    'noreply@steeplechasers.org',
#                                    ADMINS, '[scoretility] exception encountered')
#         if 'LOGGING_LEVEL_MAIL' in app.config:
#             mailloglevel = app.config['LOGGING_LEVEL_MAIL']
#         else:
#             mailloglevel = logging.ERROR
#         mail_handler.setLevel(mailloglevel)
#         mail_handler.setFormatter(Formatter('''
#         Message type:       %(levelname)s
#         Location:           %(pathname)s:%(lineno)d
#         Module:             %(module)s
#         Function:           %(funcName)s
#         Time:               %(asctime)s
        
#         Message:
        
#         %(message)s
#         '''))
#         app.logger.addHandler(mail_handler)
#         app.config['LOGGING_MAIL_HANDLER'] = mail_handler
        
#         logpath = None
#         if 'LOGGING_PATH' in app.config:
#             logpath = app.config['LOGGING_PATH']
            
#         if logpath:
#             # file rotates every Monday
#             file_handler = TimedRotatingFileHandler(logpath,when='W0',delay=True)
#             if 'LOGGING_LEVEL_FILE' in app.config:
#                 fileloglevel = app.config['LOGGING_LEVEL_FILE']
#             else:
#                 fileloglevel = logging.WARNING
#             file_handler.setLevel(fileloglevel)
#             app.logger.addHandler(file_handler)
#             app.config['LOGGING_FILE_HANDLER'] = file_handler
            
#             file_handler.setFormatter(Formatter(
#                 '%(asctime)s %(levelname)s: %(message)s '
#                 '[in %(pathname)s:%(lineno)d]'
#             ))
            
    
