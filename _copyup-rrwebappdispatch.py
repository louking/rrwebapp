#!/var/chroot/home/content/89/11476389/devhome/venv/bin/python
from flup.server.fcgi import WSGIServer
from rrwebapp.app import app
import traceback

if __name__ == '__main__':
    while True:
        try:
            WSGIServer(app).run()
            break
        except Exception,e:
            app.logger.error(traceback.format_exc())
