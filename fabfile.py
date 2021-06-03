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
    print((f'c.user={c.user} c.host={c.host} branchname={branchname}'))

    # TODO: rrwebapp should be venv, separate from application, fix for python 3
    venv_dir = f'/var/www/{c.host}/venv'
    project_dir = f'/var/www/{c.host}/{APP_NAME}'

    c.run(f'cd {project_dir} && git pull')

    if not c.run(f'cd {project_dir} && git show-ref --verify --quiet refs/heads/{branchname}', warn=True):
        raise Exit(f'branchname {branchname} does not exist')

    c.run(f'cd {project_dir} && git checkout {branchname}')
    # NOTE: this may be application specific
    c.run(f'cd {project_dir} && cp -R {JS_SOURCE} {APP_NAME}/static')
    # must source bin/activate before each command which must be done under venv
    # because each is a separate process
    c.run(f'cd {project_dir} && source {venv_dir}/bin/activate && pip install -r requirements.txt')

    versions_dir = f'{project_dir}/migrations/versions'
    if not c.run(f'test -d {versions_dir}', warn=True):
        c.run(f'mkdir -p {versions_dir}')

    c.run(f'cd {project_dir} && source {venv_dir}/bin/activate && flask db upgrade')
    c.run(f'cd {project_dir} && touch {WSGI_SCRIPT}')
