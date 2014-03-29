#!/var/chroot/home/content/89/11476389/devhome/venv/bin/python
from flup.server.fcgi import WSGIServer
from rrwebapp.app import app

if __name__ == '__main__':
    WSGIServer(app).run()
