from tests.ui_helpers import workspace_app, AuthenticatedFixture
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from streamlit.testing.v1 import AppTest
from dashboard.client import (FixtureClient, LiveClient, APIError, DEMO,
                              validate_captures, validate_verdict, validate_report)


def test_fixture_assets_and_comparison():
    client=FixtureClient()
    for r in client.captures():
        assert hashlib.sha256(client.capture_file(r['id'])).hexdigest()==r['file_sha256']
        assert r['signature']=='' and r['fixture'] is True
    assert client.verify_file('original.jpg',(DEMO/'photo.jpg').read_bytes())['status']=='VERIFIED'
    assert client.verify_file('edited.jpg',(DEMO/'photo_ai_edited.jpg').read_bytes())['status']=='CAP'
    assert client.ledger()['records']==client.captures()


def test_prepared_citations_only():
    client=FixtureClient()
    report=client.report((DEMO/'paper_real.txt').read_text())
    assert {r['status'] for r in report['results']}=={'VERIFIED','MISMATCH','UNSUPPORTED','NOT_FOUND'}
    assert {r['status'] for r in client.report((DEMO/'paper_fake_refs.txt').read_text())['results']}=={'NOT_FOUND'}
    with pytest.raises(APIError): client.report('a real paper not in fixtures')


def test_live_post_shapes_and_stream():
    session=Mock();session.request.return_value.status_code=200
    client=LiveClient('http://localhost:8000',session)
    session.request.return_value.json.return_value={'status':'CAP','reason':'No match','matched_id':None}
    client.verify_file('x.jpg',b'abc','image/jpeg')
    assert session.request.call_args.kwargs['files']=={'file':('x.jpg',b'abc','image/jpeg')}
    assert session.request.call_args.args[:2]==('POST','http://localhost:8000/verify/file')
    session.request.return_value.json.return_value={'report_id':'r','results':[]}
    client.report('hello',['id'])
    assert session.request.call_args.kwargs['json']=={'text':'hello','capture_ids':['id']}
    session.request.return_value.iter_content.return_value=[b'a',b'b']
    assert client.capture_file('a/b')==b'ab'
    assert session.request.call_args.args[1].endswith('/captures/a%2Fb/file')
    session.request.return_value.close.assert_called_once()


@pytest.mark.parametrize('validator,value',[(validate_captures,{}),(validate_captures,[{}]),
    (validate_verdict,{'status':'VERIFIED'}),(validate_verdict,{'status':'CAP'}),
    (validate_report,{'report_id':'r','results':[{'status':'MAGIC'}]})])
def test_malformed_contracts(validator,value):
    with pytest.raises(APIError): validator(value)


def test_file_limits():
    for client in [FixtureClient(),LiveClient('http://localhost')]:
        with pytest.raises(APIError): client.verify_file('empty',b'')


def test_app_input_preservation_no_duplicate_report(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE','fixture')
    original=FixtureClient.report
    calls=[]
    def spy(self,text,ids):
        calls.append(text)
        return original(self,text,ids)
    with patch.object(FixtureClient,'report',spy):
        app=workspace_app()
        app.button(key='nav_Evidence studio').click().run()
        assert not app.exception
        app.button(key='mixed_demo').click().run()
        app.button(key='citation_submit').click().run()
        assert len(calls)==1
        before=app.text_area(key='report_text').value
        app.button(key='refresh_captures').click().run()
        assert app.text_area(key='report_text').value==before
        app.button(key='citation_submit').click().run()
        assert len(calls)==1
        assert not app.exception


def test_empty_failure_recovery(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE','fixture')
    app=workspace_app()
    app.button(key='nav_Evidence studio').click().run()
    app.button(key='nav_Settings').click().run()
    app.selectbox(key='fixture_scenario').select('Empty').run()
    app.button(key='nav_Evidence studio').click().run()
    assert app.metric[0].value=='0'
    app.button(key='nav_Settings').click().run()
    app.selectbox(key='fixture_scenario').select('Disconnected').run()
    app.button(key='nav_Evidence studio').click().run()
    assert len(app.error)==2
    app.button(key='nav_Settings').click().run()
    app.selectbox(key='fixture_scenario').select('Populated').run()
    app.button(key='nav_Evidence studio').click().run()
    assert not app.error and app.metric[0].value=='3'
    assert not app.exception
