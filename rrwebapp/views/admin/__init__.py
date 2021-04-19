'''
blueprint for this folder
'''

from flask import Blueprint

bp = Blueprint('admin', __name__.split('.')[0], url_prefix='/admin', static_folder='static/admin', template_folder='templates/admin')

