from rrwebapp.model import db, ApiCredentials
from rrwebapp.resultsutils import get_runsignup_client


def test_get_runsignup_client_anonymous_when_unconfigured(dbapp):
    with dbapp.app_context():
        client = get_runsignup_client()

    assert client.key is None
    assert client.secret is None


def test_get_runsignup_client_uses_stored_credentials(dbapp):
    with dbapp.app_context():
        db.session.add(ApiCredentials(name='runsignup', key='testkey', secret='testsecret',
                                       api_reg_token='testtoken', api_reg_secret='testregsecret'))
        db.session.commit()

        client = get_runsignup_client()

    assert client.key == 'testkey'
    assert client.secret == 'testsecret'
    assert client.api_reg_token == 'testtoken'
    assert client.api_reg_secret == 'testregsecret'


def test_get_runsignup_client_passes_through_kwargs(dbapp):
    with dbapp.app_context():
        client = get_runsignup_client(debug=True)

    assert client.debug is True
