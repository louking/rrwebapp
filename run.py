'''
use this script to run the web application

Usage::

    python run.py
'''

# standard
import sys
import os.path

# homegrown
from rrwebapp import create_app
from rrwebapp.settings import Development, get_configfiles

configfiles = get_configfiles()
app = create_app(Development(configfiles), configfiles)

from loutilities.flask_helpers.blueprints import list_routes

debug = False

if debug:
    with app.app_context():
        print('listing routes from run.py')
        list_routes(app)

def main():
    # see http://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example.html
    from os import environ
    environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    app.run(debug=True)

if __name__ == "__main__":
    main()