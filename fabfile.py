###########################################################################################
# fabfile  -- deployment using Fabric
#
#   Copyright 2019 Lou King
###########################################################################################
'''
fabfile  -- deployment using Fabric
=================================================================

expecting fabric.json with following content
    {
        "connect_kwargs": {
            "key_filename": sshkeyfilename (export OpenSSH key from puttygen)
        },
        "user": "{appname}mgr" (meaning account to log in for this app)
    }

execute as follows

    fab -H <target-host> deploy

or 

    fab -H <target1>,<target2> deploy

if you need to check out a particular branch

    fab -H <target-host> deploy --branchname=<branch>
'''

from fabric import task
from invoke import Exit

APP_NAME = 'rrwebapp'
WSGI_SCRIPT = 'rrwebapp.wsgi'
JS_SOURCE = '/home/scoretility/devhome/js'

@task
def deploy(c, branchname='master'):
    print(('c.user={} c.host={} branchname={}'.format(c.user, c.host, branchname)))

    # TODO: rrwebapp should be venv, separate from application, fix for python 3
    venv_dir = '/var/www/{server}/rrwebapp'.format(server=c.host)
    project_dir = '/var/www/{server}/{appname}'.format(server=c.host, appname=APP_NAME)

    c.run('cd {} && git pull'.format(project_dir))

    if not c.run('cd {} && git show-ref --verify --quiet refs/heads/{}'.format(project_dir, branchname), warn=True):
        raise Exit('branchname {} does not exist'.format(branchname))

    c.run('cd {} && git checkout {}'.format(project_dir, branchname))
    # NOTE: this may be application specific
    c.run('cd {project_dir} && cp -R {js_source} {appname}/static'.format(project_dir=project_dir, appname=APP_NAME, js_source=JS_SOURCE))
    # must source bin/activate before each command which must be done under venv
    # because each is a separate process
    c.run('cd {} && source {}/bin/activate && pip install -r requirements.txt'.format(project_dir, venv_dir))

    versions_dir = '{project_dir}/{appname}/versioning/versions'.format(project_dir=project_dir, appname=APP_NAME)
    if not c.run('test -d {}'.format(versions_dir), warn=True):
        c.run('mkdir -p {}'.format(versions_dir))

    c.run('cd {project_dir} && source {venv_dir}/bin/activate && alembic -c {appname}/alembic.ini upgrade head'.format(project_dir=project_dir,
                                                                                                                       appname=APP_NAME,
                                                                                                                       venv_dir=venv_dir))
    c.run('cd {} && touch {}'.format(project_dir, WSGI_SCRIPT))