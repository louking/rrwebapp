def test_app_fixture_creates(app):
    assert app.config['TESTING'] is True


def test_dbapp_fixture_creates_tables(dbapp):
    from rrwebapp.model import ApiCredentials

    with dbapp.app_context():
        assert ApiCredentials.query.all() == []
