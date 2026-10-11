import hashlib,io,json
from pathlib import Path
from unittest.mock import Mock
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from cloud.api import create_app
from cloud.storage import S3Storage
from dashboard.client import validate_captures
from tests.test_cloud import api,auth,register


def image_bytes():
    out=io.BytesIO();Image.new('RGB',(16,12),'green').save(out,format='PNG');return out.getvalue()


def test_file_only_upload_labels_and_auth(api):
    c,app=api;d=register(c);data=image_bytes()
    metadata={'label':'Microscope image','experiment_id':'EXP-01','sample_id':'SAMPLE-A','notes':'Control'}
    r=c.post('/captures',headers=auth(d['token']),files={'file':('sample.png',data,'image/png')},data={'metadata':json.dumps(metadata)})
    assert r.status_code==201
    value=r.json();assert value['status']=='UNSUPPORTED'
    assert value['file_sha256']==hashlib.sha256(data).hexdigest()
    assert value['media']['width']==16
    rows=validate_captures(c.get('/captures').json())
    record=next(x for x in rows if x['id']==value['id'])
    assert record['metadata']==metadata and record['metadata_signed'] is False
    assert record['origin']=='server_receipt' and record['signature']==''
    assert c.get('/captures/'+value['id']+'/file').content==data
    assert c.get('/captures/'+value['id']+'/file',headers=auth('outsider')).status_code==404
    assert c.post('/captures',files={'file':('sample.png',data)}).status_code==403
    for filename,content in [('bad.png',b'not an image'),('file.exe',data),('bad.mp4',b'\0\0\0\x18ftypisom')]:
        assert c.post('/captures',headers=auth(d['token']),files={'file':(filename,content)}).status_code==422
    assert c.post('/captures',headers=auth(d['token']),files={'file':('x.png',data)},data={'metadata':'{"label":"x","secret":"not-allowed"}'}).status_code==422


def test_sanjay_signing_to_api_private_s3_and_verifier(api,tmp_path,monkeypatch):
    c,app=api
    import signing.record as signing
    monkeypatch.setenv('NOCAP_KEY_FILE',str(tmp_path/'device.pem'))
    monkeypatch.setenv('NOCAP_KEY_PASSPHRASE','test-passphrase-only-123')
    monkeypatch.setenv('NOCAP_DATA_DIR',str(tmp_path/'chain'))
    signing.load_key(create=True)
    d=c.post('/devices',json={'name':'Lab source','public_key':signing.public_key_pem()}).json()
    f=tmp_path/'lab.png';f.write_bytes(image_bytes())
    record=signing.make_record(f,'photo',device_id=d['id'],location='Test lab')
    objects={};sdk=Mock()
    def put(**kwargs):objects[kwargs['Key']]=kwargs['Body']
    sdk.put_object.side_effect=put
    sdk.get_object.side_effect=lambda **kw:{'Body':io.BytesIO(objects[kw['Key']])}
    store=S3Storage('private-test-bucket','us-east-2',sdk)
    target=create_app(app.state.settings,storage=store)
    try:
        with TestClient(target,headers=auth('admin-secret')) as cloud:
            fields={'record':json.dumps(record),'metadata':json.dumps({'label':'Figure 1'})}
            response=cloud.post('/captures',headers=auth(d['token']),files={'file':('lab.png',f.read_bytes())},data=fields)
            assert response.status_code==201 and response.json()['status']=='VERIFIED'
            call=sdk.put_object.call_args.kwargs
            assert call['ServerSideEncryption']=='AES256' and 'ACL' not in call
            assert next(iter(objects.values()))==f.read_bytes()
            assert cloud.get('/captures/'+record['id']+'/file').content==f.read_bytes()
            report=cloud.post('/reports',json={'text':'Figure 1 needs review.','capture_ids':[record['id']],'mode':'offline'}).json()
            assert report['analysis']['provenance'][record['id']]['valid']
            assert cloud.post('/captures',headers=auth(d['token']),files={'file':('lab.png',f.read_bytes())},data=fields).json()['duplicate']
            fields['metadata']='{"label":"changed"}'
            assert cloud.post('/captures',headers=auth(d['token']),files={'file':('lab.png',f.read_bytes())},data=fields).status_code==409
            assert cloud.post('/captures',headers=auth(d['token']),files={'file':('lab.png',f.read_bytes())}).status_code==422
    finally:target.state.engine.dispose()


def test_mp4_received_and_inspected(api,tmp_path,monkeypatch):
    import cv2,numpy as np
    path=tmp_path/'clip.mp4'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),10,(32,24))
    assert writer.isOpened()
    for _ in range(3):writer.write(np.zeros((24,32,3),dtype=np.uint8))
    writer.release()
    c,app=api;d=register(c)
    r=c.post('/captures',headers=auth(d['token']),files={'file':('clip.mp4',path.read_bytes(),'video/mp4')})
    assert r.status_code==201
    assert r.json()['media']['inspection']=='first_frame_decoded'
    assert any(x['type']=='video' for x in validate_captures(c.get('/captures').json()))
    import signing.record as signing
    monkeypatch.setenv('NOCAP_KEY_FILE',str(tmp_path/'video-key.pem'))
    monkeypatch.setenv('NOCAP_KEY_PASSPHRASE','video-test-passphrase-123')
    monkeypatch.setenv('NOCAP_DATA_DIR',str(tmp_path/'video-chain'))
    signing.load_key(create=True)
    signed=c.post('/devices',json={'name':'Signed video','public_key':signing.public_key_pem()}).json()
    record=signing.make_record(path,'video',device_id=signed['id'])
    response=c.post('/captures',headers=auth(signed['token']),files={'file':('clip.mp4',path.read_bytes(),'video/mp4')},data={'record':json.dumps(record)})
    assert response.status_code==201 and response.json()['status']=='VERIFIED'
    report=c.post('/reports',json={'text':'Video evidence needs human review.','capture_ids':[record['id']],'mode':'offline'}).json()
    assert report['analysis']['provenance'][record['id']]['valid']
    assert any('Video file integrity' in issue for issue in report['analysis']['issues'])


def test_50_mib_boundary(api):
    c,app=api;d=register(c)
    data=image_bytes();data+=b'\0'*(50*1024*1024-len(data))
    r=c.post('/captures',headers=auth(d['token']),files={'file':('large.png',data,'image/png')})
    assert r.status_code==201
    assert c.post('/captures',headers=auth(d['token']),files={'file':('large.png',data+b'x','image/png')}).status_code==413


def test_transport_matches_deployed_file_only_contract(tmp_path):
    from unittest.mock import patch
    from device.upload import upload
    path=tmp_path/'sample.png';path.write_bytes(image_bytes())
    session=Mock();session.post.return_value.status_code=201;session.post.return_value.json.return_value={'id':'receipt'}
    manager=Mock();manager.__enter__=Mock(return_value=session);manager.__exit__=Mock(return_value=False)
    with patch('device.upload.requests.Session',return_value=manager):
        assert upload('https://nocap.example','private-test-token',None,path)=={'id':'receipt'}
    assert session.post.call_count==1
    assert session.post.call_args.args==('https://nocap.example/captures',)
    assert 'file' in session.post.call_args.kwargs['files']
    assert session.post.call_args.kwargs['data']=={}
    session.post.return_value.json.return_value={'sha256':'0'*64}
    with patch('device.upload.requests.Session',return_value=manager), pytest.raises(RuntimeError,match='hash does not match'):
        upload('https://nocap.example','private-test-token',None,path)
