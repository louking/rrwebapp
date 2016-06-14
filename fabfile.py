###########################################################################################
# fabfile  -- deployment using Fabric
#
#   Copyright 2014 Lou King
###########################################################################################
'''
fabfile  -- deployment using Fabric
=================================================================

'''

from fabric.api import env, run, cd

USERNAME = 'scoretility'
APP_NAME = 'rrwebapp'
WSGI_SCRIPT = 'rrwebapp.wsgi'

project_dir = ''

def sandbox():
    server = 'sandbox.scoretility.com'
    global project_dir
    project_dir = '/var/www/{}/{}'.format(server, APP_NAME)
    env.hosts = ["{}@{}".format(USERNAME, server)]

def beta():
    server = 'beta.scoretility.com'
    global project_dir
    project_dir = '/var/www/{}/{}'.format(server, APP_NAME)
    env.hosts = ["{}@{}".format(USERNAME, server)]

def prod():
    server = 'scoretility.com'
    global project_dir
    project_dir = '/var/www/{}/{}'.format(server, APP_NAME)
    env.hosts = ["{}@{}".format(USERNAME, server)]

def deploy(branchname='master'):
    with cd(project_dir):
        run('git pull')
        run('git checkout {}'.format(branchname))
        run('cp -R ../libs/js  rrwebapp/static')
        run('cp -R ../libs/css rrwebapp/static')
        run('source bin/activate; pip install -r requirements.txt')
        run('touch {}'.format(WSGI_SCRIPT))
