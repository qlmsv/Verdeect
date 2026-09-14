from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from verdeect_core.app import create_app
from verdeect_core.models import User, Membership, ModuleGrant, OrganizationModule, WebSession, AuditEvent
from verdeect_core.auth import COOKIE_NAME, mint_dev_ticket
from verdeect_common.security import digest
from conftest import mutation_headers

API='/_platform/api'

def test_anonymous_cannot_use_identity_headers(stack):
    client=TestClient(stack.core)
    r=client.get(API+'/me',headers={'X-User':'owner','X-Role':'admin','X-Tenant':'org-a'})
    assert r.status_code==401

def test_one_use_ticket_and_server_session(stack):
    client=TestClient(stack.core)
    with stack.core.state.sessions() as db: ticket=mint_dev_ticket(db,'owner')
    r=client.post(API+'/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'})
    assert r.status_code==200
    cookie=r.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'Path=/_platform/api' in cookie and 'SameSite=lax' in cookie
    raw=client.cookies[COOKIE_NAME]
    with stack.core.state.sessions() as db:
        assert db.get(WebSession, raw) is None
        assert db.get(WebSession,digest(raw)) is not None
    assert client.post(API+'/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'}).status_code==401

def test_ticket_atomic_consumption(stack):
    with stack.core.state.sessions() as db: ticket=mint_dev_ticket(db,'owner')
    def consume(_):
        with TestClient(stack.core) as c:
            return c.post(API+'/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'}).status_code
    with ThreadPoolExecutor(max_workers=2) as ex: results=list(ex.map(consume,range(2)))
    assert sorted(results)==[200,401]

def test_meter_only_user_does_not_need_chat_permission(stack):
    info=stack.login('writer').get(API+'/me').json()
    assert info['permissions']==['meters.read','meters.readings.create']
    assert [m['id'] for m in info['modules']]==['metering']
    assert all(m['id']!='crm' for m in info['modules'])

def test_organization_admin_not_automatically_chat_admin(stack):
    info=stack.login().get(API+'/me').json()
    assert info['role']=='owner'
    assert not any('admin' in p for p in info['permissions'])

def test_organization_list_only_memberships(stack):
    assert [o['id'] for o in stack.login('reader').get(API+'/organizations').json()]==['org-a']
    assert len(stack.login().get(API+'/organizations').json())==2

def test_wrong_installation_cannot_be_selected_even_for_member(stack):
    assert stack.login().get(API+'/organizations/org-b/modules').status_code==404

def test_outsider_cannot_login_to_this_installation(stack):
    with stack.core.state.sessions() as db: ticket=mint_dev_ticket(db,'outsider')
    r=TestClient(stack.core).post(API+'/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'})
    assert r.status_code==403

@pytest.mark.parametrize('change', ['user','membership','session','module'])
def test_live_rechecks(stack,change):
    c=stack.login('reader')
    assert c.get(API+'/meters').status_code==200
    with stack.core.state.sessions() as db:
        if change=='user': db.get(User,'reader').active=False
        elif change=='membership': db.get(Membership,('org-a','reader')).active=False
        elif change=='session': db.get(WebSession,digest(c.cookies[COOKIE_NAME])).expires_at=int(time.time())-1
        else: db.get(OrganizationModule,('org-a','metering')).enabled=False
        db.commit()
    assert c.get(API+'/meters').status_code in {401,403}

@pytest.mark.parametrize('headers', [{},{'Origin':'https://evil.test'},{'Origin':'http://testserver','X-CSRF-Token':'wrong'}])
def test_csrf_blocks_mutation(stack,headers):
    c=stack.login()
    assert c.post(API+'/session/logout',headers=headers).status_code==403

def test_logout_revokes_cookie_not_just_ui(stack):
    c=stack.login(); raw=c.cookies[COOKIE_NAME]
    r=c.post(API+'/session/logout',headers=mutation_headers(c))
    assert r.status_code==200 and r.json()['global_logout'] is False
    other=TestClient(stack.core); other.cookies.set(COOKIE_NAME,raw)
    assert other.get(API+'/me').status_code==401

def test_login_rotates_previous_session(stack):
    c=stack.login(); old=c.cookies[COOKIE_NAME]
    with stack.core.state.sessions() as db: ticket=mint_dev_ticket(db,'owner')
    assert c.post(API+'/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'}).status_code==200
    assert c.cookies[COOKIE_NAME]!=old
    with stack.core.state.sessions() as db: assert db.get(WebSession,digest(old)) is None

def test_reader_cannot_manage_members(stack):
    assert stack.login('reader').get(API+'/organizations/org-a/members').status_code==403

def test_grant_revoke_and_audit(stack):
    owner=stack.login(); reader=stack.login('reader')
    assert reader.get(API+'/meters').status_code==200
    path=API+'/organizations/org-a/members/reader/module-grants/metering'
    r=owner.delete(path,headers=mutation_headers(owner))
    assert r.status_code==200
    assert reader.get(API+'/meters').status_code==403
    with stack.core.state.sessions() as db:
        event=db.scalar(select(AuditEvent))
        assert event.actor_id=='owner' and event.payload['after']==[]

def test_regrant_does_not_require_new_login(stack):
    c=stack.login(); r=stack.login('reader')
    path=API+'/organizations/org-a/members/reader/module-grants/metering'
    headers=mutation_headers(c)
    c.delete(path,headers=headers)
    assert r.get(API+'/meters').status_code==403
    assert c.put(path,json={'scopes':['meters.read']},headers=headers).status_code==200
    assert r.get(API+'/meters').status_code==200

def test_reject_unknown_privilege_and_cross_org_target(stack):
    c=stack.login(); h=mutation_headers(c)
    base=API+'/organizations/org-a/members/'
    assert c.put(base+'reader/module-grants/metering',json={'scopes':['admin']},headers=h).status_code==422
    assert c.put(base+'outsider/module-grants/metering',json={'scopes':['meters.read']},headers=h).status_code==404
    assert c.put(base+'reader/module-grants/crm',json={'scopes':['crm.access']},headers=h).status_code==404

def test_chat_grant_not_falsely_reported_applied(stack):
    c=stack.login()
    r=c.delete(API+'/organizations/org-a/members/owner/module-grants/chat',headers=mutation_headers(c))
    assert r.status_code==409

def test_non_admin_cannot_grant_itself_more_rights(stack):
    c=stack.login('reader')
    r=c.put(API+'/organizations/org-a/members/reader/module-grants/metering',json={'scopes':['meters.manage']},headers=mutation_headers(c))
    assert r.status_code==403

def test_module_outage_does_not_break_me(stack):
    def fail(_): raise httpx.ConnectError('unavailable')
    app=create_app(stack.settings,metering_transport=httpx.MockTransport(fail))
    c=stack.login(app=app)
    assert c.get(API+'/meters').status_code==503
    assert c.get(API+'/me').status_code==200

def test_no_cache_and_not_production_ready(stack):
    r=stack.login().get(API+'/me')
    assert r.headers['cache-control']=='no-store'
    assert r.json()['production_ready'] is False

def test_production_launch_is_explicitly_blocked(stack):
    with pytest.raises(ValueError,match='development-only'):
        replace(stack.settings,environment='production')

def test_dev_login_disabled_by_configuration(stack):
    app=create_app(replace(stack.settings,allow_dev_login=False))
    r=TestClient(app).post(API+'/dev/login',json={'ticket':'x'*40},headers={'Origin':'http://testserver'})
    assert r.status_code==404

def test_login_ticket_requires_origin(stack):
    with stack.core.state.sessions() as db: ticket=mint_dev_ticket(db,'owner')
    assert TestClient(stack.core).post(API+'/dev/login',json={'ticket':ticket}).status_code==403
