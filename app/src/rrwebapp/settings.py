'''
settings - define default, test and production settings

see http://flask.pocoo.org/docs/1.0/config/?highlight=production#configuration-best-practices
'''

# standard
import logging
import os.path
from os import environ

# pypi
from flask import current_app

# homegrown
from loutilities.configparser import getitems

PRODUCTNAME_TEXT = 'scoretility'

class Config(object):
    DEBUG = False
    TESTING = False

    # default database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # logging
    LOGGING_LEVEL_FILE = logging.INFO
    LOGGING_LEVEL_MAIL = logging.ERROR

    # flask-security configuration -- see https://pythonhosted.org/Flask-Security/configuration.html
    SECURITY_TRACKABLE = True
    SECURITY_DEFAULT_REMEMBER_ME = True
    # SECURITY_LOGIN_URL = False
    # SECURITY_LOGOUT_URL = False

    # javascript configuration
    # APP_JS_CONFIG = 'scores-prod-config.js'

    # avoid warning
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # branding
    THISAPP_PRODUCTNAME = '<span class="brand-all"><span class="brand-left">score</span><span class="brand-right">tility</span></span>'
    THISAPP_PRODUCTNAME_TEXT = PRODUCTNAME_TEXT

class Testing(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

    # need to set SERVER_NAME to something, else get a RuntimeError about not able to create URL adapter
    # must have following line in /etc/hosts or C:\Windows\System32\drivers\etc\hosts file
    #   127.0.0.1 dev.localhost
    SERVER_NAME = 'dev.localhost'
    
    # need a default secret key - in production replace by config file
    SECRET_KEY = "<test secret key>"

    # fake  credentials
    GOOGLE_OAUTH_CLIENT_ID = 'fake-client-id'
    GOOGLE_OAUTH_CLIENT_SECRET = 'fake-client-secret'

    # need to allow logins in flask-security. see https://github.com/mattupstate/flask-security/issues/259
    LOGIN_DISABLED = False

class RealDb(Config):
    def __init__(self, configfiles):
        if type(configfiles) == str:
            configfiles = [configfiles]

        # connect to database based on configuration
        config = {}
        for configfile in configfiles:
            config.update(getitems(configfile, 'database'))
        dbuser = config['dbuser']
        with open(f'/run/secrets/appdb-password') as pw:
            password = pw.readline().strip()
        dbserver = config['dbserver']
        dbname = config['dbname']
        # app.logger.debug('using mysql://{uname}:*******@{server}/{dbname}'.format(uname=dbuser,server=dbserver,dbname=dbname))
        db_uri = 'mysql://{uname}:{pw}@{server}/{dbname}'.format(uname=dbuser, pw=password, server=dbserver,
                                                                 dbname=dbname)
        self.SQLALCHEMY_DATABASE_URI = db_uri

        # # uncomment when working on #426
        # # https://flask-sqlalchemy.palletsprojects.com/en/2.x/binds/
        # userdbuser = config['userdbuser']
        # userpassword = config['userdbpassword']
        # userdbserver = config['userdbserver']
        # userdbname = config['userdbname']
        # userdb_uri = 'mysql://{uname}:{pw}@{server}/{dbname}'.format(uname=userdbuser, pw=userpassword, server=userdbserver,
        #                                                          dbname=userdbname)
        # self.SQLALCHEMY_BINDS = {
        #     'users': userdb_uri
        # }

class Development(RealDb):
    # normally True, set to False for test of applogging
    DEBUG = True

class Production(RealDb):
    pass


def productname():
    return PRODUCTNAME_TEXT

def get_configfiles():
    appname = environ['APP_NAME']

    abspath = os.path.abspath('/config')
    configpath = os.path.join(abspath, f'{appname}.cfg')

    # userconfigpath = os.path.join('config', 'users.cfg')
    # userconfigpath first so configpath can override
    configfiles = [configpath]
    return configfiles
