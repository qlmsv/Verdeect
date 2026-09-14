#!/usr/bin/env python3
"""Development bootstrap. Not a production tenant-provisioning tool."""
from pathlib import Path
import argparse
import json
import os
import secrets
import sys
ROOT=Path(__file__).resolve().parents[1]
for p in ['packages/python','services/platform_api','services/metering_api']:sys.path.insert(0,str(ROOT/p))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from verdeect_common.db import database
from verdeect_core.models import Base, User, Organization, Membership, OrganizationModule, ModuleGrant
from verdeect_core.auth import mint_dev_ticket


def private_write(path:Path,content:str):
    if path.exists():raise RuntimeError(f'Refusing to replace an existing secret/config: {path}')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(content)


def initialize(state:Path):
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name in ['platform-data','metering-data','keys']:(state/name).mkdir(exist_ok=True,mode=0o700)
    private=state/'keys/delegation-private.pem';public=state/'keys/delegation-public.pem'
    if private.exists()!=public.exists():raise RuntimeError('Incomplete key pair. Restore it instead of silently rotating it.')
    if not private.exists():
        key=Ed25519PrivateKey.generate()
        private_write(private,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode())
        private_write(public,key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode())
    url='sqlite:///'+str(state/'platform-data/platform.db')
    engine,sessions=database(url);Base.metadata.create_all(engine)
    with sessions() as db:
        if not db.get(User,'dev-owner'):
            db.add(User(id='dev-owner',issuer='https://identity.invalid',subject='dev-owner',email='developer@example.test',name='Разработчик',active=True));db.flush()
        if not db.get(Organization,'demo'):
            db.add(Organization(id='demo',name='Демо-организация',origin='http://localhost:8080',active=True));db.flush()
        if not db.get(Membership,('demo','dev-owner')):
            db.add(Membership(org_id='demo',user_id='dev-owner',role='owner',active=True))
        for module,scopes in [('chat',['chat.use']),('metering',['meters.read','meters.manage','meters.readings.create'])]:
            if not db.get(OrganizationModule,('demo',module)):db.add(OrganizationModule(org_id='demo',module_id=module,enabled=True))
            if not db.get(ModuleGrant,('demo','dev-owner',module)):db.add(ModuleGrant(org_id='demo',user_id='dev-owner',module_id=module,scopes=scopes))
        db.commit()
    config=state/'compose.env'
    if not config.exists():
        private_write(config,'\n'.join([
            'APP_ENV=development','INSTALLATION_ORG_ID=demo','PUBLIC_ORIGIN=http://localhost:8080',
            'ALLOW_DEV_LOGIN=true','COOKIE_SECURE=false',f'DEV_STATE_DIR={state}',
            f'LOCAL_UID={getattr(os,"getuid",lambda:1000)()}',f'LOCAL_GID={getattr(os,"getgid",lambda:1000)()}',
            'WEBUI_SECRET_KEY='+secrets.token_urlsafe(48),'OAUTH_COOKIE_SECRET='+secrets.token_urlsafe(48),
            'OIDC_ISSUER=','OIDC_CLIENT_ID=','OIDC_CLIENT_SECRET=','']) )
    engine.dispose()
    print('Development state initialized:',state)
    print('Generate a single-use ticket: python scripts/platformctl.py ticket')
    print('No production mode, GitHub write, or server deployment was performed.')


def ticket(state:Path,user:str):
    if not (state/'platform-data/platform.db').exists():raise RuntimeError('Run init first')
    engine,sessions=database('sqlite:///'+str(state/'platform-data/platform.db'))
    with sessions() as db:print(mint_dev_ticket(db,user))
    engine.dispose()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir',type=Path,default=ROOT/'.dev')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init');t=sub.add_parser('ticket');t.add_argument('--user',default='dev-owner')
    a=p.parse_args();state=a.state_dir.resolve()
    if a.command=='init':initialize(state)
    else:ticket(state,a.user)
if __name__=='__main__':main()
