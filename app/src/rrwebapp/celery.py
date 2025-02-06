"""
celery - define for tasks, celery app
========================================
"""
# standard
from os import environ
import os.path

# pypi
from celery import Celery
from celery.signals import worker_process_init
from loutilities.configparser import getitems

# home grown
from . import create_app
from .settings import Production, get_configfiles

celeryapp = Celery(
    'rrwebapp',
    include=['rrwebapp.tasks'])

appname = environ['APP_NAME']

abspath = os.path.abspath('/config')
configpath = os.path.join(abspath, f'{appname}.cfg')
dbconfig = getitems(configpath, 'database')
celeryconfig = getitems(configpath, 'celery')

dbuser = dbconfig['dbuser']
dbserver = dbconfig['dbserver']
dbname = dbconfig['dbname']
with open(f'/run/secrets/appdb-password') as pw:
    dbpassword = pw.readline().strip()
celeryconfig['result_backend'] = f'db+mysql://{dbuser}:{dbpassword}@{dbserver}/{dbname}'

username = celeryconfig['username']
brokerserver = celeryconfig['brokerserver']
brokerhost = celeryconfig['brokerhost']
with open(f'/run/secrets/rabbitmq-app-password') as pw:
    password = pw.readline().strip()
celeryconfig['broker_url'] =  f'amqp://{username}:{password}@{brokerhost}/{brokerserver}'
# print(f'broker_url = {celeryconfig['broker_url']}')

celeryapp.conf.update(celeryconfig)


# adapted from https://stackoverflow.com/a/37649636/799921
@worker_process_init.connect
def init_celery_flask_app(**kwargs):
    configfiles = get_configfiles()
    app = create_app(Production(configfiles), configfiles)
    app.app_context().push()