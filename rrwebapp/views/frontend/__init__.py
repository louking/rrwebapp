'''
blueprint for this folder
'''

from flask import Blueprint

bp = Blueprint('frontend', __name__.split('.')[0], url_prefix='/', static_folder='static/frontend', template_folder='templates/frontend')

