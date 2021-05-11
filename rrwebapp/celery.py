"""
celery - define for tasks, celery app
========================================
"""
# standard
from os.path import join

# pypi
from celery import Celery
from celery.signals import worker_process_init
from loutilities.configparser import getitems

# home grown
from . import create_app
from .settings import Production, get_configfiles

celery = Celery(
    'rrwebapp',
    include=['rrwebapp.tasks'])

configpath = join('config', 'rrwebapp.cfg')
celeryconfig = getitems(configpath, 'celery')
celery.conf.update(celeryconfig)

# adapted from https://stackoverflow.com/a/37649636/799921
@worker_process_init.connect
def init_celery_flask_app(**kwargs):
    configfiles = get_configfiles()
    app = create_app(Production(configfiles), configfiles)
    app.app_context().push()