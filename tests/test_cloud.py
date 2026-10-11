import hashlib,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert,select
from cloud.api import create_app,digest
from cloud.bootstrap import initialize
from cloud.config import Settings
from cloud import db
from cloud.storage import S3Storage,LocalStorage
from unittest.mock import Mock

@pytest.fixture
def api(tmp_path):
    settings=Settings(database_url='sqlite:///'+str(tmp_path/'db.sqlite'),media_dir=str(tmp_path/'media'))
    initialize(settings,'admin-secret')
    app=create_app(settings)
    with app.state.engine.begin() as c:
        c.execute(insert(db.orgs).values(id='other',name='Other org'))
        for id,org,role in [('outsider','other','admin'),('collab','org_demo','collaborator'),('reviewer','org_demo','reviewer')]:
            c.execute(insert(db.members).values(id=id,org_id=org,name=id,email=id+'@example.test',role=role,active=True))
            c.execute(insert(db.tokens).values(digest=digest(id),org_id=org,member_id=id,revoked=False))
    with TestClient(app,headers={'Authorization':'Bearer admin-secret'}) as client:
        yield client,app
    app.state.engine.dispose()

def auth(token): return {'Authorization':'Bearer '+token}
def register(c): return c.post('/devices',json={'name':'Test Pi','location':'Local simulator'}).json()
def record(device,id='cap_test'):
    data=b'original bytes'
    return data,dict(id=id,type='reading',file_name='reading.json',file_sha256=hashlib.sha256(data).hexdigest(),captured_at='2026-10-11T12:00:00+00:00',device_id=device,location='Simulator',prev_hash='0'*64,record_hash=hashlib.sha256(id.encode()).hexdigest(),signature='')
def send(c,d,r,data): return c.post('/captures',headers=auth(d['token']),data={'record':json.dumps(r)},files={'file':('reading.json',data)})

def test_auth_and_tenant_isolation(api):
    c,a=api
    assert c.get('/me',headers=auth('wrong')).status_code==401
    assert c.get('/captures',headers=auth('outsider')).json()==[]
    assert c.get('/captures/demo_1/file',headers=auth('outsider')).status_code==404
    assert c.get('/work-items/work_sources/comments',headers=auth('outsider')).status_code==404
    assert c.post('/members',headers=auth('collab'),json={'name':'New','email':'new@example.test'}).status_code==403
    assert c.get('/ledger',headers=auth('outsider')).json()['merkle_root'] is None

def test_workbench_concurrency_roles_comments(api):
    c,a=api
    item=c.post('/work-items',json={'title':'Review paper','section':'Methods','owner_id':'collab'}).json()
    assert item['version']==1
    assert c.patch('/work-items/'+item['id'],headers=auth('collab'),json={'version':1,'status':'Approved','owner_id':'collab'}).status_code==403
    path='/work-items/'+item['id']
    assert c.patch(path,json={'version':1,'status':'In progress','owner_id':'collab'}).status_code==200
    assert c.patch(path,json={'version':1,'status':'Approved','owner_id':'collab'}).status_code==409
    assert c.patch(path,headers=auth('reviewer'),json={'version':2,'status':'Approved','owner_id':'collab'}).status_code==200
    assert c.post(path+'/comments',json={'body':'Checked the original bytes.'}).status_code==201
    assert len(c.get(path+'/comments').json())==1
    assert c.post('/work-items',json={'title':'Bad ownership','section':'X','owner_id':'outsider'}).status_code==404
    assert c.get('/activity').json()[0]['action']=='comment.added'

def test_device_to_api_to_dashboard_and_idempotency(api):
    c,a=api;d=register(c);data,r=record(d['id'])
    assert c.get('/members',headers=auth(d['token'])).status_code==403
    assert c.post('/devices/'+d['id']+'/heartbeat',headers=auth(d['token']),json={'firmware':'test'}).status_code==200
    assert send(c,d,r,data).json()['status']=='UNSUPPORTED'
    assert send(c,d,r,data).json()['duplicate'] is True
    assert c.get('/captures/cap_test/file').content==data
    assert c.get('/captures').json()[-1]['id']=='cap_test'
    assert c.post('/verify/file',files={'file':('test',data)}).json()['status']=='UNSUPPORTED'
    assert c.post('/verify/file',files={'file':('test',data+b'x')}).json()['status']=='CAP'
    assert c.get('/devices').json()[0]['connection'] in {'Recent heartbeat','Never connected'}
    r['location']='changed';assert send(c,d,r,data).status_code==409
    assert c.post('/devices/'+d['id']+'/revoke').status_code==200
    assert send(c,d,r,data).status_code==401

def test_tampered_file_chain_and_device_rejected(api):
    c,a=api;d=register(c);data,r=record(d['id'])
    assert send(c,d,r,data+b'bad').status_code==422
    r['device_id']='someone_else';assert send(c,d,r,data).status_code==403
    r['device_id']=d['id'];r['prev_hash']='1'*64
    assert send(c,d,r,data).status_code==409
    assert len(c.get('/captures').json())==3

def test_live_ingestion_fails_closed_without_signer(api):
    c,a=api;d=register(c);data,r=record(d['id']);a.state.settings.demo=False
    assert send(c,d,r,data).status_code==503
    a.state.settings.demo=True
    assert len(c.get('/captures').json())==3

def test_storage_failure_rolls_back_head(api):
    c,a=api;d=register(c);data,r=record(d['id'])
    original=a.state.storage.put;a.state.storage.put=Mock(side_effect=OSError('storage unavailable'))
    assert send(c,d,r,data).status_code==503
    a.state.storage.put=original
    assert send(c,d,r,data).status_code==201

def test_schema_and_bounded_upload(api):
    c,a=api;d=register(c);data,r=record(d['id']);r['captured_at']='2026-10-11T10:00:00'
    assert send(c,d,r,data).status_code==422
    a.state.settings.max_upload=2
    assert c.post('/verify/file',files={'file':('test',b'abc')}).status_code==413
    assert c.get('/captures?limit=99999').status_code==422
    assert c.post('/members',json={'name':'x','email':'invalid'}).status_code==422

def test_reports_ledger_download_contract(api):
    c,a=api
    from ledger.merkle import merkle_root
    led=c.get('/ledger').json()
    assert led['merkle_root']==merkle_root([r['record_hash'] for r in led['records']])
    assert led['chain_ok'] is None and led['anchor_tx'] is None and led['fixture']
    result=c.post('/reports',json={'text':Path('demo/paper_real.txt').read_text(),'capture_ids':['demo_1'],'mode':'demo'}).json()
    assert len(result['results'])==4
    assert c.get('/reports/'+result['report_id']).json()['results']==result['results']
    assert c.get('/reports/'+result['report_id'],headers=auth('outsider')).status_code==404
    assert c.post('/ledger/anchor').status_code==503

def test_s3_adapter_does_not_publish_objects():
    s=Mock();s.get_object.return_value={'Body':Mock()};s.get_object.return_value['Body'].read.return_value=b'abc'
    store=S3Storage('test-bucket','us-east-2',s);store.put('opaque/key',b'abc');assert store.get('opaque/key')==b'abc';store.delete('opaque/key')
    assert s.put_object.call_args.kwargs['ServerSideEncryption']=='AES256'
    assert 'ACL' not in s.put_object.call_args.kwargs
    s.get_object.return_value['Body'].close.assert_called_once()

def test_configuration_and_path_guards(tmp_path):
    with pytest.raises(ValueError): Settings(database_url='postgresql+psycopg://u:p@host/db').validate()
    with pytest.raises(ValueError): Settings(demo=False).validate()
    Settings(database_url='postgresql+psycopg://u:p@host/db?sslmode=verify-full&sslrootcert=/ca.pem',demo=False).validate()
    with pytest.raises(ValueError): LocalStorage(tmp_path).get('../elsewhere')

def test_token_expiry_and_member_provisioning(api,tmp_path):
    from datetime import datetime,timezone,timedelta
    from sqlalchemy import update
    from cloud.manage import issue
    c,a=api;output=tmp_path/'token.txt'
    with a.state.engine.begin() as conn: issue(conn,'org_demo','collab',str(output),1)
    token=output.read_text().strip()
    assert c.get('/me',headers=auth(token)).json()['role']=='collaborator'
    assert output.stat().st_mode & 0o777==0o600
    with a.state.engine.begin() as conn:
        conn.execute(update(db.tokens).where(db.tokens.c.digest==digest(token)).values(expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()))
    assert c.get('/me',headers=auth(token)).status_code==401

def test_ambiguous_commit_preserves_original(api,monkeypatch):
    from sqlalchemy.engine import Connection
    c,a=api;d=register(c);data,r=record(d['id'])
    real_commit=Connection.commit;fired=False
    def uncertain(self):
        nonlocal fired
        real_commit(self)
        if not fired:
            fired=True
            raise OSError('Commit acknowledgement lost')
    monkeypatch.setattr(Connection,'commit',uncertain)
    result=send(c,d,r,data)
    assert result.status_code==201
    assert c.get('/captures/cap_test/file').content==data

def test_authentication_token_requires_https(monkeypatch):
    from dashboard.client import LiveClient,APIError
    with pytest.raises(APIError): LiveClient('http://example.com',token='secret')
    LiveClient('https://example.com',token='secret')

def test_request_body_limit_rejects_before_ingestion(tmp_path):
    settings=Settings(database_url='sqlite:///'+str(tmp_path/'bounded.db'),media_dir=str(tmp_path/'media'),max_upload=2)
    initialize(settings,'key');app=create_app(settings)
    with TestClient(app,headers=auth('key')) as c:
        response=c.post('/reports',content=b'x'*70000,headers={'Content-Type':'application/json'})
        assert response.status_code in {400,413}
        assert c.get('/summary').json()['captures']==3
    app.state.engine.dispose()
