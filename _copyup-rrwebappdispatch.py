#!/var/chroot/home/content/89/11476389/devhome/venv/bin/python
from flup.server.fcgi import WSGIServer
from rrwebapp.app import app
import os.path

class ScriptNameStripper(object):
   def __init__(self, app):
       self.app = app

   def __call__(self, environ, start_response):
       environ['SCRIPT_NAME'] = '/standings'    # edit here for non-standard location
       return self.app(environ, start_response)

import time
from loutilities import timeu
tu = timeu.asctime('%Y-%m-%d %H:%M:%S')
os.environ['RRWEBAPP_SETTINGS'] = os.path.abspath('./rrwebapp.cfg')
app.config.from_envvar('RRWEBAPP_SETTINGS')
app.configtime = tu.epoch2asc(time.time())
app.configpath = os.environ['RRWEBAPP_SETTINGS']

# must set up logging after setting configuration
from rrwebapp import applogging
applogging.setlogging()

# must be after setting app.config
app = ScriptNameStripper(app)

if __name__ == '__main__':
    # create the server
    server = WSGIServer(app)
    
    # and run it
    server.run()
