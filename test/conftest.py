import os

# APP_NAME/APP_VER are normally supplied by Docker Compose's .env; set them here so the
# rrwebapp package (which reads them at import time) also works for local/CI pytest runs
os.environ.setdefault('APP_NAME', 'rrwebapp')
os.environ.setdefault('APP_VER', 'test')

import pytest
from flask import Flask

from rrwebapp.model import db

# deliberately NOT using rrwebapp.create_app(): it unconditionally registers the admin
# blueprint, which imports views/admin/member.py -> tasks.py -> celery.py, and celery.py
# reads /config/<APP_NAME>.cfg and Docker secrets files at module import time -- paths that
# only exist inside the container. A bare Flask app with just db bound is enough for
# model/view-function-level tests that don't need the full app (routing, security, mail, etc).


@pytest.fixture
def app():
    """Minimal Flask app with rrwebapp's db bound, no blueprints/extensions registered."""
    app = Flask('rrwebapp')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    db.init_app(app)
    yield app


@pytest.fixture
def dbapp(app):
    """app fixture with a fresh in-memory database created for the test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
