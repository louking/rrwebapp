from fabric.api import env, run, cd

USERNAME = 'scoretility'
APP_NAME = 'rrwebapp'
WSGI_SCRIPT = 'rrwebapp.wsgi'

def deploy(project_dir, branchname):
    with cd(project_dir):
        run('git pull')
        run('git checkout {}'.format(branchname))
        run('cp -R ../libs/js  rrwebapp/static')
        run('cp -R ../libs/css rrwebapp/static')
        run('source bin/activate; pip install -r requirements.txt')
        run('touch %s' % WSGI_SCRIPT)

def deployproduction(branchname='master'):
    server = 'scoretility.com'
    project_dir = '/var/www/%s/html/%s' % (server, APP_NAME)
    env.hosts = ["%s@%s" % (USERNAME, server)]
    deploy(project_dir, branchname)

def deploybeta(branchname='master'):
    server = 'beta.scoretility.com'
    project_dir = '/var/www/%s/html/%s' % (server, APP_NAME)
    env.hosts = ["%s@%s" % (USERNAME, server)]
    deploy(project_dir, branchname)
