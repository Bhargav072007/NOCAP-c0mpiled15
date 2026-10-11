"""Access and single-source regressions for the public entry flow."""
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from dashboard.client import APIError
from dashboard.workbench import primary_device
from tests.ui_helpers import workspace_app

APP = Path('dashboard/app.py').resolve()
ME = {'id': 'member', 'name': 'Reviewer', 'role': 'reviewer', 'organization': 'Test', 'demo': False}


def test_public_and_direct_workspace_gate(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE', 'live')
    monkeypatch.setenv('NOCAP_SERVICE_DEMO', '0')
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert not any(b.key == 'nav_Evidence studio' for b in app.button)
    app.query_params['page'] = 'workspace'
    app.run()
    assert app.query_params['page'] == 'login'
    assert not any(b.key == 'enter_demo' for b in app.button)
    assert not any(b.key == 'nav_Overview' for b in app.button)


def test_bad_token_never_enters_workspace(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE', 'live')
    monkeypatch.setenv('NOCAP_SERVICE_DEMO', '0')
    app = AppTest.from_file(APP)
    app.query_params['page'] = 'login'
    app.run()
    with patch('dashboard.client.LiveClient.json', side_effect=APIError('Invalid or expired token')):
        app.text_input[0].set_value('invalid-token')
        app.button[0].click().run()
    assert any('Invalid or expired' in e.value for e in app.error)
    assert 'workspace_token' not in app.session_state
    assert not any(b.key == 'nav_Overview' for b in app.button)


def test_valid_token_signout_and_revocation(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE', 'live')
    monkeypatch.setenv('NOCAP_SERVICE_DEMO', '0')
    def request(self, method, path, **kwargs):
        if path == '/me': return ME
        raise APIError('Not included in entry test')
    app = AppTest.from_file(APP)
    app.query_params['page'] = 'login'
    with patch('dashboard.client.LiveClient.json', request):
        app.run()
        app.text_input[0].set_value('test-personal-token')
        app.button[0].click().run()
        assert app.session_state.workspace_token == 'test-personal-token'
        assert any(b.key == 'nav_Overview' for b in app.button)
        assert 'test-personal-token' not in str(app.query_params)
    with patch('dashboard.client.LiveClient.json', side_effect=APIError('Invalid or expired token')):
        app.run()
        assert not any(b.key == 'nav_Overview' for b in app.button)
        next(b for b in app.button if b.label == 'Return to sign in').click().run()
        assert 'workspace_token' not in app.session_state
        assert app.session_state.page == 'login'


def test_demo_access_and_no_devices_navigation(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE', 'fixture')
    app = AppTest.from_file(APP)
    app.query_params['page'] = 'login'
    app.run()
    app.button(key='enter_demo').click().run()
    assert not app.exception
    assert app.session_state.demo_access
    assert {b.label for b in app.button if b.key and b.key.startswith('nav_')} == {'Overview', 'Research papers', 'Evidence studio', 'Team workbench', 'Settings'}
    next(b for b in app.button if b.label == 'Sign out').click().run()
    assert 'demo_access' not in app.session_state
    assert app.session_state.page == 'login'


def test_primary_source_does_not_guess_between_real_devices():
    def source(id, fixture=False): return {'id': id, 'enabled': True, 'fixture': fixture}
    rows = [source('synthetic-generator', True), source('actual')]
    assert primary_device(rows)['id'] == 'actual'
    rows.append(source('second'))
    assert primary_device(rows) is None
    assert primary_device(rows, 'actual')['id'] == 'actual'
    assert primary_device(rows, 'missing') is None
    assert primary_device([source('synthetic-generator', True)])['fixture']


def test_preferences_survive_navigation(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE', 'fixture')
    app = workspace_app()
    app.button(key='nav_Settings').click().run()
    app.toggle(key='still').set_value(True).run()
    app.toggle(key='auto').set_value(True).run()
    app.button(key='nav_Evidence studio').click().run()
    app.run()
    assert app.session_state.still is True
    assert app.session_state.auto is True
    app.button(key='nav_Settings').click().run()
    assert app.toggle(key='still').value is True
