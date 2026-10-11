from pathlib import Path
from streamlit.testing.v1 import AppTest
from dashboard.client import FixtureClient, APIError


def workspace_app():
    app = AppTest.from_file(Path('dashboard/app.py').resolve())
    app.session_state.page = 'workspace'
    app.session_state.demo_access = True
    app.session_state.route = 'Evidence studio'
    return app.run()


class AuthenticatedFixture(FixtureClient):
    mode = 'live'

    def json(self, method, path, **kwargs):
        if path == '/me':
            return {'id': 'test', 'name': 'Test reviewer', 'role': 'reviewer', 'organization': 'Test', 'demo': True}
        raise APIError('No workspace extension fixture for '+path)

    def captures(self, **kwargs):
        return super().captures()
