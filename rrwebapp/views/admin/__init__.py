'''
blueprint for this folder
'''

from flask import Blueprint

bp = Blueprint('admin', __name__.split('.')[0], url_prefix='/admin', static_folder='static/admin', template_folder='templates/admin')

from . import userrole
from . import services
from . import location
from . import member
from . import results
from . import resultsanalysis
from . import race
from . import club
from . import standings
from . import debug