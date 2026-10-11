"""Public entry and session navigation. No credential is included in a URL."""
import os
from dashboard.motion import ambient_ribbon
from dashboard.product import product_home
import streamlit as st
from dashboard.client import APIError, LiveClient, make_client


def go(page, route=None):
    st.session_state.page = page
    st.query_params['page'] = page
    if route:
        st.session_state.route = route


def sign_out():
    for key in list(st.session_state):
        del st.session_state[key]
    go('login')


def brand():
    return '<a class="nc-brand" href="?page=home" target="_self" aria-label="NoCap home"><span class="nc-monogram" aria-hidden="true">N</span><span>NoCap</span></a>'


def landing(is_demo):
    with st.container(key='public'):
        st.html(product_home(brand()))
        if is_demo:
            st.caption('Local demo available · synthetic evidence · live hardware and verification are not connected.')


def login(is_demo):
    with st.container(key='login'):
        left, right = st.columns([1.15, 1], gap='large', vertical_alignment='center')
        with left:
            st.html(f'''<div class="nc-login-intro">{brand()}<h1>Enter the<br>workspace.</h1><p>A focused place for original evidence,<br>shared reviews, and the decisions behind your research.</p><a href="?page=home" target="_self">← Back to NoCap</a></div>''')
        with right, st.container(key='login_card', border=True):
            st.html(f'<div class="nc-login-ambient"><div><h2 class="nc-login-title">Welcome back.</h2></div>{ambient_ribbon(compact=True)}</div>')
            st.caption('Use the workspace access token from your administrator.')
            with st.form('workspace_signin'):
                credential = st.text_input('Workspace access token', type='password', placeholder='Enter your access token', key='login_token')
                submitted = st.form_submit_button('Continue', type='primary', use_container_width=True)
            if submitted:
                if not credential.strip():
                    st.error('Enter your workspace access token to continue.')
                else:
                    try:
                        candidate = LiveClient(os.getenv('NOCAP_API', 'http://localhost:8000'), token=credential.strip())
                        candidate.json('GET', '/me')
                        st.session_state.workspace_token = credential.strip()
                        st.session_state.pop('demo_access', None)
                        go('workspace', 'Overview')
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
            if is_demo:
                st.divider()
                st.markdown('**Explore the local workspace**')
                st.caption('Try the evidence and team workflows with saved synthetic data. No account required.')
                if st.button('Open local demo', key='enter_demo', use_container_width=True):
                    try:
                        client = make_client('Populated')
                        if client.mode == 'live':
                            client.json('GET', '/me')
                        st.session_state.demo_access = True
                        go('workspace', 'Overview')
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
            else:
                st.divider()
                st.caption('Need access? Ask your workspace administrator for a personal token.')
