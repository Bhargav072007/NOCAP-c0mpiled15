from pathlib import Path
import sys, os, hashlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from dotenv import load_dotenv
from dashboard.client import APIError, make_client, LiveClient
from dashboard.ui import styles, ledger_view, captures_view, verify_view, citation_view
from dashboard.workbench import heading, identity_card, overview, team_view, integration_view
from dashboard.shell import landing, login, go, sign_out, brand

load_dotenv()
st.set_page_config(page_title='NoCap — Proof, not vibes.', page_icon='N', layout='wide', initial_sidebar_state='auto')
ROUTES = {
    'Overview': ('Your evidence at a glance.', 'space_dashboard'),
    'Evidence studio': ('Original captures, file comparisons, citations, and the audit trail.', 'folder_open'),
    'Team workbench': ('Shared reviews. Clear ownership.', 'group'),
    'Settings': ('Workspace connection and preferences.', 'settings'),
}
is_demo = os.getenv('NOCAP_MODE', 'fixture') == 'fixture' or os.getenv('NOCAP_SERVICE_DEMO') == '1'
page = st.query_params.get('page', st.session_state.get('page', 'home'))
if page not in {'home', 'login', 'workspace'}:
    page = 'home'
st.session_state.page = page
# Preserve preferences when their widgets are absent on another route.
for preference in ('opaque', 'still', 'auto', 'fixture_scenario'):
    if preference in st.session_state:
        st.session_state[preference] = st.session_state[preference]
styles(st.session_state.get('opaque', False), st.session_state.get('still', False))
if page == 'home':
    landing(is_demo)
    st.stop()
if page == 'login':
    login(is_demo)
    st.stop()
if not st.session_state.get('workspace_token') and not (is_demo and st.session_state.get('demo_access')):
    go('login')
    st.rerun()
scenario = st.session_state.get('fixture_scenario', 'Populated')
auto = st.session_state.get('auto', False)
try:
    client = (LiveClient(os.getenv('NOCAP_API', 'http://localhost:8000'), token=st.session_state.workspace_token)
              if st.session_state.get('workspace_token') else make_client(scenario))
    me = {'id': 'fixture', 'name': 'Local preview', 'role': 'admin', 'organization': 'Standalone fixtures'}
    if client.mode == 'live':
        me = client.json('GET', '/me')
        client.workspace_extensions = True
        client.demo = bool(me.get('demo', False))
        is_demo = client.demo
except APIError as exc:
    with st.container(key='access_error'):
        st.title('Workspace connection unavailable')
        st.error(str(exc))
        st.caption('Your work is saved. Retry the connection or sign in again.')
        st.button('Retry connection')
        st.button('Return to sign in', on_click=sign_out)
    st.stop()
identity = (client.mode, getattr(client, 'base_url', 'fixture'), scenario, hashlib.sha256(getattr(client, 'token', '').encode()).hexdigest())
if st.session_state.get('client_identity') != identity:
    for key in ['verify_result', 'verified_fingerprint', 'verified_filename', 'report_result', 'reported_fingerprint', 'preview_cache', 'motion_events', 'displayed_root', 'capture_cursors']:
        st.session_state.pop(key, None)
    st.session_state.client_identity = identity
if st.session_state.get('route') not in ROUTES:
    st.session_state.route = 'Overview'
def navigate(route):
    st.session_state.route = route
with st.sidebar:
    st.html('<div class="nc-sidebar-brand">'+brand()+'<small>Evidence workspace</small></div>')
    with st.container(key='sidebar_nav'):
        for label, (_, icon) in ROUTES.items():
            st.button(label, key='nav_'+label, use_container_width=True,
                      type='primary' if st.session_state.route == label else 'secondary',
                      on_click=navigate, args=(label,))
    with st.container(key='sidebar_footer'):
        st.html('<div class="nc-eyebrow">WORKSPACE</div>')
        st.markdown('**'+me['organization']+'**')
        st.caption('Local demo · synthetic evidence' if is_demo else 'Authenticated workspace')
        st.button('Back to home', on_click=go, args=('home',), use_container_width=True)
        st.button('Sign out', on_click=sign_out, use_container_width=True)
route = st.session_state.route
with st.container(key='workspace'):
    a, b = st.columns([3, 1.5])
    with a: heading(route, ROUTES[route][0])
    with b: identity_card(me)
    if is_demo:
        st.html('<div class="nc-mode-banner">LOCAL DEMO <span>Synthetic sample captures. Review mode and coverage are shown with each report.</span></div>')
    if route == 'Overview': overview(client, me)
    elif route == 'Team workbench': team_view(client, me)
    elif route == 'Settings':
        integration_view(client)
        with st.expander('Display & refresh preferences'):
            st.toggle('Poll captures every 10 seconds', key='auto')
            st.toggle('Reduce transparency', key='opaque')
            st.toggle('Reduce motion', key='still')
        if is_demo:
            with st.expander('Demo scenarios'):
                st.selectbox('Fixture scenario', ['Populated', 'Empty', 'Disconnected', 'Malformed', 'Slow', 'Long list'], key='fixture_scenario', disabled=client.mode != 'fixture')
    elif route == 'Evidence studio':
        with st.container(key='navigation'):
            captures, verify, citations, ledger = st.tabs(['Live captures', 'Verify a file', 'Citation check', 'Audit ledger'])
            with captures:
                if auto: st.caption('Capture polling · every 10 seconds')
                st.fragment(run_every='10s' if auto else None)(captures_view)(client)
            with verify: verify_view(client)
            with citations: citation_view(client)
            with ledger: ledger_view(client)
