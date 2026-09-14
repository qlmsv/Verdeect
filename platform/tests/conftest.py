from dataclasses import replace
from types import SimpleNamespace
import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from verdeect_core.app import create_app
from verdeect_core.config import Settings
from verdeect_core.models import User, Organization, Membership, OrganizationModule, ModuleGrant
from verdeect_core.auth import mint_dev_ticket
from verdeect_metering.app import create_app as create_metering, Settings as MeterSettings

@pytest.fixture
def stack(tmp_path):
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    meter = create_metering(MeterSettings(f'sqlite:///{tmp_path}/meters.db', 'org-a', public, 'test'))
    settings = Settings(database_url=f'sqlite:///{tmp_path}/platform.db', installation_org_id='org-a',
        public_origin='http://testserver', metering_url='http://metering', delegation_private_key=private,
        environment='test', allow_dev_login=True)
    core = create_app(settings, metering_transport=httpx.ASGITransport(app=meter))
    with core.state.sessions() as db:
        db.add_all([User(id=i, issuer='https://id.test', subject=i, name=i.title(), email=f'{i}@example.test', active=True)
            for i in ['owner','writer','reader','outsider']])
        db.add_all([Organization(id='org-a', name='A', origin='http://testserver', active=True),
                    Organization(id='org-b', name='B', origin='https://b.example.test', active=True)])
        db.flush()
        db.add_all([Membership(org_id='org-a', user_id=i, role='owner' if i=='owner' else 'member', active=True)
            for i in ['owner','writer','reader']])
        db.add(Membership(org_id='org-b', user_id='outsider', role='owner', active=True))
        db.add(Membership(org_id='org-b', user_id='owner', role='member', active=True))
        db.add_all([OrganizationModule(org_id='org-a',module_id=m,enabled=True) for m in ['chat','metering']])
        db.add_all([
            ModuleGrant(org_id='org-a',user_id='owner',module_id='metering',scopes=['meters.read','meters.manage','meters.readings.create']),
            ModuleGrant(org_id='org-a',user_id='owner',module_id='chat',scopes=['chat.use']),
            ModuleGrant(org_id='org-a',user_id='writer',module_id='metering',scopes=['meters.read','meters.readings.create']),
            ModuleGrant(org_id='org-a',user_id='reader',module_id='metering',scopes=['meters.read']),
        ])
        db.commit()
    clients=[]
    def login(user='owner', app=None):
        app=app or core
        client=TestClient(app)
        clients.append(client)
        with app.state.sessions() as db:
            ticket=mint_dev_ticket(db,user)
        r=client.post('/_platform/api/dev/login',json={'ticket':ticket},headers={'Origin':'http://testserver'})
        assert r.status_code==200, r.text
        return client
    value=SimpleNamespace(core=core,meter=meter,settings=settings,private=private,public=public,login=login)
    yield value
    for c in clients: c.close()
    core.state.engine.dispose(); meter.state.engine.dispose()


def mutation_headers(client):
    return {'Origin':'http://testserver','X-CSRF-Token':client.get('/_platform/api/me').json()['csrf_token']}
