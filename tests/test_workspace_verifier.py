"""Real dashboard client → authenticated API → Segment 3 → persisted report."""
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from dashboard.client import LiveClient, APIError
from verifier.provenance import canonical
from tests.test_cloud import api, auth, send

TEXT='This manuscript needs supporting evidence.\n\nReferences\n[1] Example Author. An unreviewed reference. 2020.'

class Session:
    def __init__(self, client): self.client=client
    def request(self, method, url, **kwargs):
        kwargs['follow_redirects']=kwargs.pop('allow_redirects')
        kwargs.pop('timeout',None)
        kwargs.pop('stream',None)
        response=self.client.request(method,url,**kwargs)
        response.iter_content=response.iter_bytes
        return response


def dashboard(c, token='admin-secret'):
    return LiveClient('http://localhost',session=Session(c),token=token)


def test_real_offline_report_roundtrip_and_isolation(api):
    c, app=api
    ui=dashboard(c)
    with patch('verifier.llm.get_judge',side_effect=AssertionError('Offline must not call a provider')):
        report=ui.report(TEXT, mode='offline')
    assert report['fixture'] is False
    assert report['workspace_demo'] is True
    assert report['analysis']['network_requests']==0
    assert report['results'][0]['backend_status']=='NEEDS_REVIEW'
    assert report['results'][0]['status']=='UNSUPPORTED'
    assert ui.saved_report(report['report_id'])['analysis']==report['analysis']
    assert ui.reports()[0]['report_id']==report['report_id']
    assert dashboard(c,'outsider').reports()==[]
    with pytest.raises(APIError,match='404'): dashboard(c,'outsider').saved_report(report['report_id'])
    assert c.post('/reports',headers=auth('outsider'),json={'text':TEXT,'capture_ids':['demo_1']}).status_code==404


def test_uploaded_manuscript_and_invalid_uploads(api):
    c, app=api;ui=dashboard(c)
    for name, data in [('paper.txt',TEXT.encode()),('paper.md',TEXT.encode())]:
        report=ui.report_file(name,data,mode='offline')
        assert report['document']['file_sha256']==hashlib.sha256(data).hexdigest()
        assert report['analysis']['coverage']['reference_entries']==1
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    pdf=PdfWriter();page=pdf.add_blank_page(612,792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 72 700 Td (A manuscript for review.) Tj ET')
    page[NameObject('/Contents')]=stream
    output=io.BytesIO();pdf.write(output)
    pdf_report=ui.report_file('paper.pdf',output.getvalue(),mode='offline')
    assert 'A manuscript for review.' in pdf_report['analysis']['coverage']['unlinked_statements']
    from docx import Document
    doc=Document();doc.add_paragraph('Methods need review.');out=io.BytesIO();doc.save(out)
    report=ui.report_file('paper.docx',out.getvalue(),mode='offline')
    assert report['analysis']['coverage']['unlinked_statement_count']>0
    for name,data in [('bad.pdf',b'not a PDF'),('x.exe',b'executable'),('empty.txt',b'  '),('long.txt',b'x'*50001),('paths.md',b'![x](/etc/passwd)')]:
        assert c.post('/reports/file',files={'file':(name,data)}).status_code==422
    assert c.post('/reports/file',files={'file':('x.txt',b'x')},data={'capture_ids':'not-json'}).status_code==422


def test_hybrid_is_explicit_and_provider_failure_is_reviewable(api):
    c,app=api
    assert c.post('/reports',json={'text':TEXT,'mode':'hybrid'}).status_code==503
    app.state.settings.verifier_mode='hybrid'
    from verifier.llm import ModelError
    with patch('verifier.llm.get_judge',side_effect=ModelError('Provider unavailable')):
        result=dashboard(c).report(TEXT,mode='hybrid')
    assert not result['analysis']['api']['configured']
    assert any(r['check']=='API' and r['status']=='UNSUPPORTED' for r in result['results'])
    assert not result['fixture']
    assert 'Provider unavailable' in result['analysis']['issues']
    assert c.get('/integration').json()['hybrid_enabled'] is True


def test_signed_capture_chain_and_file_match_reach_verifier(api):
    c, app=api
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    device=c.post('/devices',json={'name':'Integration source','public_key':public}).json()
    previous='0'*64
    for index in range(2):
        data=b'x\n1\n2\n3\n'
        record={'id':f'signed_{index}','type':'reading','file_name':'observations.csv',
                'file_sha256':hashlib.sha256(data).hexdigest(),'captured_at':'2026-10-11T12:00:00+00:00',
                'device_id':device['id'],'location':'Local test','prev_hash':previous}
        record['record_hash']=hashlib.sha256(canonical(record)).hexdigest()
        record['signature']=key.sign(bytes.fromhex(record['record_hash'])).hex()
        response=send(c,device,record,data)
        assert response.status_code==201 and response.json()['status']=='VERIFIED'
        previous=record['record_hash']
    ui=dashboard(c)
    assert ui.verify_file('copy.csv',data)['status']=='VERIFIED'
    result=ui.report('The observations.csv dataset needs a reviewer.', ['signed_1'],mode='offline')
    # Selecting only the final capture still verifies the entire enrolled chain.
    assert set(result['analysis']['provenance'])=={'signed_0','signed_1'}
    assert all(v['valid'] for v in result['analysis']['provenance'].values())
    assert result['analysis']['dataset_inventory'][0]['id']=='signed_1'
    record['id']='forged'
    record['prev_hash']=previous
    assert send(c,device,record,data).status_code==422
    assert c.get('/reports',headers=auth(device['token'])).status_code==403


def test_hybrid_full_pipeline_uses_backend_context(api):
    c, app=api;app.state.settings.verifier_mode='hybrid'
    # Only external provider/retrieval boundaries are doubles; the actual hybrid
    # engine, report mapping, authentication and persistence run unchanged.
    from types import SimpleNamespace
    from verifier.science import CATEGORIES
    judge=SimpleNamespace(provider='test-double',model='contract-test',store=False)
    judge.json=lambda *args,**kwargs: ({'assessments':[], 'coverage':[
        {'category':category,'state':'INSUFFICIENT_EVIDENCE','reason':'No linked source.'} for category in CATEGORIES]}, {'provider':'test-double'})
    with patch('verifier.llm.get_judge',return_value=judge), patch('verifier.online.verify',return_value=[]), patch('verifier.auto_data.extract_data_claims',return_value=([],[])):
        result=dashboard(c).report(TEXT,mode='hybrid')
    assert result['analysis']['api']['provider']=='test-double'
    assert result['analysis']['org_id']=='org_demo'
    assert result['analysis']['scientific_assessment']['certifies_scientific_accuracy'] is False
    assert dashboard(c).saved_report(result['report_id'])['analysis']==result['analysis']


def test_saved_reports_survive_new_api_instance(api):
    c,app=api
    result=dashboard(c).report(TEXT,mode='offline')
    from cloud.api import create_app
    from fastapi.testclient import TestClient
    reopened=create_app(app.state.settings)
    try:
        with TestClient(reopened,headers=auth('admin-secret')) as other:
            assert other.get('/reports/'+result['report_id']).json()['analysis']==result['analysis']
    finally: reopened.state.engine.dispose()


def test_frontend_runs_and_reopens_real_report(api,monkeypatch):
    c, backend=api
    monkeypatch.setenv('NOCAP_MODE','live')
    monkeypatch.setenv('NOCAP_SERVICE_DEMO','1')
    monkeypatch.setenv('NOCAP_API','http://localhost')
    monkeypatch.setenv('NOCAP_TOKEN','admin-secret')
    from tests.ui_helpers import workspace_app
    with patch('dashboard.client.requests.Session',return_value=Session(c)):
        app=workspace_app()
        assert not app.exception
        app.text_area(key='report_text').set_value(TEXT)
        app.button(key='citation_submit').click().run()
        assert not app.exception and not app.error
        result=app.session_state.report_result
        assert result['analysis']['network_requests']==0
        assert result['results'][0]['backend_status']=='NEEDS_REVIEW'
        assert c.get('/reports').json()[0]['report_id']==result['report_id']
        app.button(key='citation_submit').click().run()
        assert len(c.get('/reports').json())==1
        next(b for b in app.button if b.label=='Open saved report').click().run()
        assert not app.exception
        assert app.session_state.report_source=='saved'
        assert app.session_state.report_result['report_id']==result['report_id']
