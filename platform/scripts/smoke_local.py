#!/usr/bin/env python3
"""Run actual core-to-meter HTTP on loopback; no Docker/IdP/OpenWebUI involved."""
from pathlib import Path
import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
for p in ['packages/python','services/platform_api','services/metering_api','scripts']:sys.path.insert(0,str(ROOT/p))
import httpx
from platformctl import initialize
from verdeect_common.db import database
from verdeect_core.auth import mint_dev_ticket


def available_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    outcomes=[];processes=[]
    with tempfile.TemporaryDirectory(prefix='verdeect-smoke-') as directory:
        state=Path(directory)
        with contextlib.redirect_stdout(io.StringIO()):initialize(state)
        cp,mp=available_port(),available_port()
        while mp==cp:mp=available_port()
        origin=f'http://127.0.0.1:{cp}';meter_origin=f'http://127.0.0.1:{mp}'
        env={**os.environ,'PYTHONPATH':os.pathsep.join(str(ROOT/p) for p in ['packages/python','services/platform_api','services/metering_api']),
             'APP_ENV':'development','INSTALLATION_ORG_ID':'demo','ALLOW_DEV_LOGIN':'true','PUBLIC_ORIGIN':origin,
             'METERING_URL':meter_origin,'COOKIE_SECURE':'false','OIDC_ISSUER':''}
        configs=[('verdeect_metering.app:from_env',mp,{**env,'DATABASE_URL':'sqlite:///'+str(state/'metering-data/metering.db'),
            'DELEGATION_PUBLIC_KEY_FILE':str(state/'keys/delegation-public.pem')}),
            ('verdeect_core.app:from_env',cp,{**env,'DATABASE_URL':'sqlite:///'+str(state/'platform-data/platform.db'),
            'DELEGATION_PRIVATE_KEY_FILE':str(state/'keys/delegation-private.pem')})]
        try:
            for module,port,config in configs:
                processes.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--factory','--host','127.0.0.1','--port',str(port),'--no-access-log'],env=config,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            with httpx.Client(base_url=origin,trust_env=False,timeout=5) as c:
                for attempt in range(60):
                    try:
                        if c.get('/healthz').status_code==200 and httpx.get(meter_origin+'/healthz',trust_env=False).status_code==200:break
                    except httpx.RequestError:pass
                    time.sleep(.1)
                else:raise RuntimeError('Local processes failed to start')
                outcomes.append('two_real_HTTP_processes_started')
                assert c.get('/_platform/api/meters').status_code==401
                outcomes.append('anonymous_access_denied')
                engine,sessions=database('sqlite:///'+str(state/'platform-data/platform.db'))
                with sessions() as db:ticket=mint_dev_ticket(db,'dev-owner')
                engine.dispose()
                r=c.post('/_platform/api/dev/login',json={'ticket':ticket},headers={'Origin':origin});assert r.status_code==200,r.text
                info=c.get('/_platform/api/me').json();csrf=info['csrf_token']
                outcomes.append('opaque_session_and_org_context')
                h={'Origin':origin,'X-CSRF-Token':csrf,'Idempotency-Key':str(uuid.uuid4())}
                r=c.post('/_platform/api/meters',json={'label':'Live HTTP smoke','serial':'SMOKE-1','unit':'m3'},headers=h)
                assert r.status_code==201,r.text;meter=r.json()['id']
                outcomes.append('BFF_to_meter_signed_delegation')
                path=f'/_platform/api/meters/{meter}/readings';h['Idempotency-Key']=str(uuid.uuid4())
                body={'value':'123.456','measured_at':'2026-01-01T12:00:00+00:00'}
                a=c.post(path,json=body,headers=h);b=c.post(path,json=body,headers=h)
                assert a.status_code==b.status_code==201 and a.json()==b.json()
                assert len(c.get(path).json())==1
                outcomes.append('reading_retry_is_idempotent')
                assert c.post(path,json=body,headers={'Origin':origin}).status_code==403
                outcomes.append('CSRF_rejected')
                assert httpx.get(meter_origin+'/meters',trust_env=False).status_code==401
                outcomes.append('direct_meter_access_rejected')
                assert c.post('/_platform/api/session/logout',headers={'Origin':origin,'X-CSRF-Token':csrf}).status_code==200
                assert c.get('/_platform/api/me').status_code==401
                outcomes.append('server_session_logout')
        finally:
            for p in processes:p.terminate()
            for p in processes:
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
    print(json.dumps({'result':'passed','checks':outcomes,'excluded':['live IdP','OpenWebUI frontend/backend','Docker','browser UI','production']},indent=2))
if __name__=='__main__':main()
