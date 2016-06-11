from fabric.api import env, run, cd

USERNAME = 'scoretility'
APP_NAME = 'rrwebapp'
WSGI_SCRIPT = 'rrwebapp.wsgi'

def deployproduction():
    server = 'scoretility.com'
    project_dir = '/var/www/%s/html/%s' % (server, APP_NAME)
    env.hosts = ["%s@%s" % (USERNAME, server)]
    with cd(project_dir):
        run('git pull')
        run('source bin/activate; pip install -r requirements.txt')
        run('touch %s' % WSGI_SCRIPT)

def deploybeta(branchname='master'):
    server = 'beta.scoretility.com'
    project_dir = '/var/www/%s/html/%s' % (server, APP_NAME)
    env.hosts = ["%s@%s" % (USERNAME, server)]
    with cd(project_dir):
        run('git pull')
        run('git checkout {}'.format(branchname))
        run('source bin/activate; pip install -r requirements.txt')
        run('touch %s' % WSGI_SCRIPT)