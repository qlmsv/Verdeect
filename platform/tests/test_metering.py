from datetime import datetime, timezone
import time
import uuid
import jwt
import pytest
from fastapi.testclient import TestClient
from verdeect_common.security import mint_delegation, TOKEN_ISSUER
from verdeect_metering.models import Meter
from conftest import mutation_headers
API='/_platform/api'

def create_meter(c,serial='123'):
    r=c.post(API+'/meters',json={'label':'Холодная вода','serial':serial,'unit':'m3'},
        headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())})
    assert r.status_code==201,r.text
    return r.json()['id']

def reading(value='123.456'):
    return {'value':value,'measured_at':'2026-01-01T12:00:00+00:00','kind':'normal'}

def test_full_bff_meter_reading_flow(stack):
    c=stack.login(); meter=create_meter(c)
    payload=reading()
    r=c.post(f'{API}/meters/{meter}/readings',json=payload,headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())})
    assert r.status_code==201,r.text
    assert r.json()['value']=='123.456' and r.json()['author_id']=='owner'
    rows=c.get(f'{API}/meters/{meter}/readings').json()
    assert len(rows)==1 and rows[0]['meter_id']==meter

def test_repeated_reading_has_no_duplicates(stack):
    c=stack.login(); meter=create_meter(c)
    path=f'{API}/meters/{meter}/readings'; h={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}
    a=c.post(path,json=reading(),headers=h); b=c.post(path,json=reading(),headers=h)
    assert a.status_code==b.status_code==201 and a.json()==b.json()
    assert len(c.get(path).json())==1
    assert c.post(path,json=reading('999'),headers=h).status_code==409

def test_meter_creation_idempotency(stack):
    c=stack.login(); h={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}
    body={'label':'Электричество','serial':'E1','unit':'kWh'}
    a=c.post(API+'/meters',json=body,headers=h); b=c.post(API+'/meters',json=body,headers=h)
    assert a.status_code==b.status_code==201 and a.json()==b.json()
    assert len(c.get(API+'/meters').json())==1

def test_unknown_meter_returns_404(stack):
    c=stack.login()
    assert c.get(f'{API}/meters/{uuid.uuid4()}/readings').status_code==404

def test_read_only_cannot_submit(stack):
    owner=stack.login(); meter=create_meter(owner); c=stack.login('reader')
    assert c.post(f'{API}/meters/{meter}/readings',json=reading(),headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}).status_code==403

def test_writer_cannot_create_meters(stack):
    c=stack.login('writer')
    assert c.post(API+'/meters',json={'label':'X','serial':'1','unit':'m3'},headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}).status_code==403

@pytest.mark.parametrize('value', ['-1','NaN','Infinity','1.1234567',123.45])
def test_invalid_decimal_rejected(stack,value):
    c=stack.login(); meter=create_meter(c)
    r=c.post(f'{API}/meters/{meter}/readings',json=reading(value),headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())})
    assert r.status_code==422

def test_idempotency_key_required(stack):
    c=stack.login(); meter=create_meter(c)
    assert c.post(f'{API}/meters/{meter}/readings',json=reading(),headers=mutation_headers(c)).status_code==422

def test_identity_fields_in_payload_rejected(stack):
    c=stack.login()
    body={'label':'X','serial':'1','unit':'m3','org_id':'org-b'}
    assert c.post(API+'/meters',json=body,headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}).status_code==422

def test_foreign_object_is_not_readable_even_in_wrong_database(stack):
    meter=str(uuid.uuid4())
    with stack.meter.state.sessions() as db:
        db.add(Meter(id=meter,org_id='org-b',label='Foreign',serial='B1',unit='m3',location='')); db.commit()
    c=stack.login()
    assert c.get(f'{API}/meters/{meter}/readings').status_code==404
    assert c.get(API+'/meters').json()==[]

def test_meter_backend_does_not_accept_user_headers_or_session_cookie(stack):
    c=TestClient(stack.meter)
    assert c.get('/meters',headers={'X-User':'owner','X-Role':'admin'}).status_code==401

def test_delegation_audience_and_scope(stack):
    c=TestClient(stack.meter)
    wrong=mint_delegation(stack.private,'org-b','owner',['meters.read'])
    assert c.get('/meters',headers={'Authorization':'Bearer '+wrong}).status_code==401
    no_scope=mint_delegation(stack.private,'org-a','owner',[])
    assert c.get('/meters',headers={'Authorization':'Bearer '+no_scope}).status_code==403
    valid=mint_delegation(stack.private,'org-a','owner',['meters.read'])
    assert c.get('/meters',headers={'Authorization':'Bearer '+valid}).status_code==200

@pytest.mark.parametrize('mode',['expired','too_long','wrong_signature','wrong_algorithm'])
def test_invalid_token(stack,mode):
    c=TestClient(stack.meter); now=int(time.time())
    claims={'iss':TOKEN_ISSUER,'aud':'metering:org-a','sub':'owner','org':'org-a','scope':['meters.read'],'iat':now,'nbf':now,'exp':now+30,'jti':'x'}
    if mode=='expired': claims.update(iat=now-60,nbf=now-60,exp=now-30)
    if mode=='too_long': claims['exp']=now+3600
    if mode=='wrong_algorithm': token=jwt.encode(claims,'x'*32,algorithm='HS256')
    elif mode=='wrong_signature':
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        token=jwt.encode(claims,Ed25519PrivateKey.generate(),algorithm='EdDSA')
    else: token=jwt.encode(claims,stack.private,algorithm='EdDSA')
    assert c.get('/meters',headers={'Authorization':'Bearer '+token}).status_code==401

def test_reset_reading_can_be_lower(stack):
    c=stack.login(); meter=create_meter(c)
    for value,kind in [('900','normal'),('1','reset')]:
        body=reading(value); body['kind']=kind
        assert c.post(f'{API}/meters/{meter}/readings',json=body,headers={**mutation_headers(c),'Idempotency-Key':str(uuid.uuid4())}).status_code==201
    assert len(c.get(f'{API}/meters/{meter}/readings').json())==2
