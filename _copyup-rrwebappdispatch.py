#!/var/chroot/home/content/89/11476389/devhome/venv/bin/python
from flup.server.fcgi import WSGIServer
from rrwebapp.app import app

class ScriptNameStripper(object):
   def __init__(self, app):
       self.app = app

   def __call__(self, environ, start_response):
       environ['SCRIPT_NAME'] = '/standings'
       return self.app(environ, start_response)

app = ScriptNameStripper(app)

if __name__ == '__main__':
    WSGIServer(app).run()
