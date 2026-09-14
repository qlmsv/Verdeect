"""Controller tests with a simulated OIDC provider, NOT live Keycloak acceptance."""
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse
from verdeect_core.app import create_app
from verdeect_core.auth import COOKIE_NAME
from verdeect_common.security import safe_return_path

class MockVerifiedOIDC:
    def __init__(self,subject='owner',issuer='https://id.test'):
        self.subject=subject;self.issuer=issuer
    async def authorize_redirect(self,request,redirect_uri):
        request.session['test_state']='expected'
        return RedirectResponse('https://id.test/authorize')
    async def authorize_access_token(self,request):
        if request.query_params.get('state')!=request.session.get('test_state'):
            raise ValueError('bad state')
        return {'id_token':'mock-id-token-not-a-real-credential','access_token':'mock-access-token',
            'userinfo':{'iss':self.issuer,'sub':self.subject,'email':'owner@example.test'}}

def oidc_app(stack,subject='owner',issuer='https://id.test'):
    settings=replace(stack.settings,oidc_issuer='https://id.test',oidc_client_id='platform',
        oidc_client_secret='test-client-secret',oauth_cookie_secret='x'*48)
    return create_app(settings,oauth_client=MockVerifiedOIDC(subject,issuer))

def test_oidc_controller_creates_server_session_mock(stack):
    c=TestClient(oidc_app(stack))
    assert c.get('/_platform/api/auth/login',follow_redirects=False).status_code==307
    r=c.get('/_platform/api/auth/callback?state=expected',follow_redirects=False)
    assert r.status_code==303
    assert COOKIE_NAME in c.cookies
    assert c.get('/_platform/api/me').json()['user']['id']=='owner'
    cookies=' '.join(r.headers.get_list('set-cookie'))
    assert 'mock-access-token' not in cookies and 'mock-id-token' not in cookies

def test_oidc_controller_rejects_bad_state_mock(stack):
    c=TestClient(oidc_app(stack));c.get('/_platform/api/auth/login',follow_redirects=False)
    assert c.get('/_platform/api/auth/callback?state=wrong').status_code==401
    assert COOKIE_NAME not in c.cookies

def test_oidc_controller_does_not_link_by_same_email_mock(stack):
    c=TestClient(oidc_app(stack,subject='different-subject'))
    c.get('/_platform/api/auth/login',follow_redirects=False)
    assert c.get('/_platform/api/auth/callback?state=expected').status_code==403

def test_oidc_controller_checks_expected_issuer_mock(stack):
    c=TestClient(oidc_app(stack,issuer='https://other-id.test'))
    c.get('/_platform/api/auth/login',follow_redirects=False)
    assert c.get('/_platform/api/auth/callback?state=expected').status_code==401

def test_oidc_controller_requires_membership_mock(stack):
    c=TestClient(oidc_app(stack,subject='outsider'))
    c.get('/_platform/api/auth/login',follow_redirects=False)
    assert c.get('/_platform/api/auth/callback?state=expected').status_code==403

@pytest.mark.parametrize('path',['//evil.test','https://evil.test','/%2f%2fevil.test','/a/../b','/a/%252e%252e/b','/\\evil.test','/a\nLocation: evil'])
def test_return_path_rejects_escape(path):
    with pytest.raises(ValueError):safe_return_path(path)

def test_return_path_accepts_native_deep_link():
    assert safe_return_path('/_platform/apps/meters?meter=42')=='/_platform/apps/meters?meter=42'
