from flask import g
from flask_principal import Identity

from rrwebapp.accesscontrol import (
    UpdateClubDataPermission, ViewClubDataPermission, UpdateClubDataNeed, ViewClubDataNeed,
)


def test_update_permission_has_update_need_for_club():
    perm = UpdateClubDataPermission(5)
    assert UpdateClubDataNeed(5) in perm.needs


def test_view_permission_has_view_need_for_club():
    perm = ViewClubDataPermission(5)
    assert ViewClubDataNeed(5) in perm.needs


def test_update_permission_can_true_when_identity_provides_need(dbapp):
    with dbapp.test_request_context():
        identity = Identity('user1')
        identity.provides.add(UpdateClubDataNeed(5))
        g.identity = identity

        assert UpdateClubDataPermission(5).can() is True
        # a different club's need does not satisfy this permission
        assert UpdateClubDataPermission(6).can() is False


def test_view_permission_can_false_for_anonymous_identity(dbapp):
    with dbapp.test_request_context():
        g.identity = Identity(None)

        assert ViewClubDataPermission(5).can() is False
