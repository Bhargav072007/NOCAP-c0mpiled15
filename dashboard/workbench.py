"""Persistent collaboration UI. Every mutation crosses the authenticated API."""
from html import escape
import json
import os
from datetime import datetime
import streamlit as st
from dashboard.client import APIError
from dashboard.motion import ambient_ribbon

STATUSES=['To review','In progress','Changes requested','Approved']

def call(client,method,path,**kwargs):
    return client.json(method,path,**kwargs)

def available(client):
    if client.mode=='fixture':
        st.info('Team and device persistence require the local API. Start scripts/run_local.py to open the full-stack demo.')
        return False
    return True

def heading(title,description):
    st.html(f'<div class="nc-page-title"><h1>{escape(title)}</h1><p>{escape(description)}</p></div>')

def identity_card(me):
    st.html(f'<div class="nc-identity-with-motion">{ambient_ribbon(compact=True)}<div class="nc-identity"><span class="nc-avatar">{escape(me["name"][:2].upper())}</span><div><strong>{escape(me["name"])}</strong><small>{escape(me["role"].title())} / {escape(me["organization"])}</small></div></div></div>')

def member_cards(members,items):
    cols=st.columns(3)
    for i,m in enumerate(members):
        assigned=sum(r['owner_id']==m['id'] and r['status']!='Approved' for r in items)
        with cols[i%3]:
            st.html(f'<article class="nc-person"><span class="nc-avatar">{escape(m["name"][:2].upper())}</span><strong>{escape(m["name"])}</strong><small>{escape(m["role"].title())}</small><p>{assigned} open in this review page</p><span>{escape(m["email"])}</span></article>')

@st.dialog('Add a workspace member')
def add_member(client):
    st.caption('Creates a membership record. No invitation email is sent and no sign-in credential is issued.')
    with st.form('member_form'):
        name=st.text_input('Name',max_chars=120);email=st.text_input('Email',max_chars=254)
        role=st.selectbox('Workspace role',['collaborator','reviewer','admin'])
        if st.form_submit_button('Add member',type='primary'):
            try: call(client,'POST','/members',json={'name':name,'email':email,'role':role});st.rerun()
            except APIError as exc: st.error(str(exc))

@st.dialog('Create a review')
def create_review(client,members,captures):
    owners={m['id']:m['name'] for m in members}
    with st.form('review_form'):
        title=st.text_input('Review title',max_chars=200)
        section=st.text_input('Paper section',max_chars=120)
        owner=st.selectbox('Assign to',list(owners),format_func=owners.get)
        priority=st.selectbox('Priority',['Normal','High','Urgent'])
        links={'':'No linked capture',**{r['id']:r['file_name'] for r in captures}}
        linked=st.selectbox('Linked evidence',list(links),format_func=links.get)
        if st.form_submit_button('Create review',type='primary'):
            try:
                result=call(client,'POST','/work-items',json={'title':title,'section':section,'owner_id':owner,'priority':priority,'capture_id':linked or None})
                st.session_state.review_selected=result['id'];st.rerun()
            except APIError as exc: st.error(str(exc))

@st.fragment
def team_view(client,me):
    if not available(client): return
    try:
        members=call(client,'GET','/members')
        offset=st.session_state.get('work_offset',0)
        items=call(client,'GET',f'/work-items?limit=50&offset={offset}')
        names={m['id']:m['name'] for m in members}
        a,b,c=st.columns([5,1.5,1.5])
        a.caption('Shared reviews / ownership / decisions')
        if b.button('New review',type='primary',use_container_width=True): create_review(client,members,client.captures())
        if c.button('Add member',disabled=me['role']!='admin',use_container_width=True): add_member(client)
        people,reviews=st.tabs(['Review workbench','People & collaborators'])
        with people:
            if not items: st.info('No reviews on this page. Create a review to assign ownership.')
            else:
                st.dataframe([{'Review':r['title'],'Section':r['section'],'Owner':names.get(r['owner_id'],'Unknown'),'Status':r['status'],'Priority':r['priority']} for r in items],hide_index=True,use_container_width=True)
            prev,next_=st.columns(2)
            if offset > 0 and prev.button('Previous reviews'): st.session_state.work_offset=max(0,offset-50);st.rerun(scope='fragment')
            if len(items) >= 50 and next_.button('Next reviews'): st.session_state.work_offset=offset+50;st.rerun(scope='fragment')
            if items:
                selected=st.selectbox('Open review',[r['id'] for r in items],format_func=lambda id:next(r['title'] for r in items if r['id']==id),key='review_selected')
                item=next(r for r in items if r['id']==selected)
                left,right=st.columns([1.1,1],gap='large')
                with left,st.container(border=True):
                    st.subheader(item['title']);st.caption(item['section']+' / '+item['priority']+' priority')
                    st.caption('Linked capture: '+(item['capture_id'] or 'None'))
                    with st.form('update_review_'+selected):
                        allowed=STATUSES if me['role'] in {'admin','reviewer'} else [s for s in STATUSES if s!='Approved']
                        status=st.selectbox('Review status',allowed,index=allowed.index(item['status']) if item['status'] in allowed else 0)
                        owner=st.selectbox('Review owner',list(names),index=list(names).index(item['owner_id']),format_func=names.get,disabled=me['role']=='collaborator')
                        if st.form_submit_button('Save review',type='primary',disabled=me['role']=='collaborator' and item['owner_id']!=me['id']):
                            call(client,'PATCH','/work-items/'+selected,json={'version':item['version'],'status':status,'owner_id':owner});st.rerun(scope='fragment')
                    st.caption('Approval is a teammate decision, not automated evidence verification.')
                with right,st.container(border=True):
                    st.subheader('Discussion')
                    comments=call(client,'GET','/work-items/'+selected+'/comments')
                    if not comments: st.caption('Start a focused conversation about this review.')
                    for comment in comments:
                        st.markdown('**'+names.get(comment['author_id'],'Member')+'**');st.text(comment['body']);st.caption(short_time(comment['created_at']))
                    with st.form('comment_'+selected,clear_on_submit=True):
                        body=st.text_area('Review comment',max_chars=5000,height=100)
                        if st.form_submit_button('Post comment'):
                            call(client,'POST','/work-items/'+selected+'/comments',json={'body':body});st.rerun(scope='fragment')
        with reviews:
            st.caption('Role-based workspace memberships. Demo profiles use reserved example.test addresses; no real attendance or live presence is implied.')
            member_cards(members,items)
    except APIError as exc: st.error(str(exc));st.button('Retry workbench',key='retry_team')

def primary_device(rows, configured_id=None):
    """Choose only an explicit source or an unambiguous physical source.

    Historic synthetic enrollments are retained; they are never presented as a
    fleet. A local calibration source can illustrate the single-device state.
    """
    if configured_id:
        return next((r for r in rows if r['id'] == configured_id), None)
    physical = [r for r in rows if r['enabled'] and not r['fixture']]
    if len(physical) == 1:
        return physical[0]
    if physical:
        return None
    return next((r for r in rows if r['enabled'] and r['fixture'] and r['id'] == 'synthetic-generator'), None)


def short_time(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%b %d · %H:%M UTC')
    except (ValueError, AttributeError):
        return value or 'Not reported'


def open_section(route):
    st.session_state.route = route


def overview(client, me):
    if not available(client):
        st.caption('Open Evidence studio to explore the standalone preview.')
        st.button('Open evidence studio', on_click=open_section, args=('Evidence studio',), type='primary')
        return
    try:
        summary = call(client, 'GET', '/summary')
        reviews = call(client, 'GET', '/work-items?limit=3')
        members = call(client, 'GET', '/members')
        events = call(client, 'GET', '/activity')
        names = {m['id']: m['name'] for m in members}
        values = [summary['captures'], summary['open_reviews'], summary['approved'], summary['members']]
        with st.container(key='overview_metrics'):
            for col, label, value in zip(st.columns(4), ['Evidence records', 'Open reviews', 'Approved reviews', 'Team members'], values):
                with col, st.container(key='metric_'+label.replace(' ', '_')):
                    st.metric(label, value)
        with st.container(border=True, key='review_queue'):
            title, action = st.columns([4, 1])
            title.subheader('Review queue')
            action.button('View workbench', on_click=open_section, args=('Team workbench',), use_container_width=True)
            st.caption('Latest assignments and the next decisions to make.')
            st.html('<div class="nc-table-head"><span>REVIEW / OWNER</span><span>STATUS</span></div>')
            for r in reviews:
                status_class = 'approved' if r['status'] == 'Approved' else 'pending'
                st.html(f'<div class="nc-task-row"><div><strong>{escape(r["title"])}</strong><small>{escape(r["section"])} <span class="nc-separator">/</span> {escape(names.get(r["owner_id"], "Member"))}</small></div><span class="nc-status {status_class}">{escape(r["status"])}</span></div>')
            if not reviews:
                st.caption('No reviews yet. Create one in the team workbench.')
        left, right = st.columns([1.6, 1], gap='medium')
        with left, st.container(border=True, key='recent_activity'):
            st.subheader('Recent activity')
            labels = {'demo.workspace_seeded': 'Workspace created', 'work.created': 'Review created', 'work.updated': 'Review updated', 'comment.created': 'Comment added', 'member.created': 'Member added', 'capture.created': 'Capture received', 'device.enrolled': 'Source enrolled', 'report.created': 'Citation report created'}
            for e in events[:4]:
                action = labels.get(e['action'], e['action'].replace('.', ' ').replace('_', ' ').capitalize())
                st.html(f'<div class="nc-activity"><div>{escape(action)}<small>{escape(names.get(e["actor"], "Source"))}</small></div><time>{escape(short_time(e["created_at"]))}</time></div>')
            if not events:
                st.caption('Workspace actions will appear here.')
        with right, st.container(border=True, key='review_progress'):
            st.subheader('Review progress')
            approved, total = summary['approved'], summary['reviews']
            st.html(f'<div class="nc-completion"><strong>{approved}</strong><span>/ {total} reviews</span></div>')
            st.progress(approved / total if total else 0)
            st.caption('Approved by your team. Evidence verification is reported separately.')
            st.button('Inspect evidence', on_click=open_section, args=('Evidence studio',), use_container_width=True)
        st.button('Refresh overview', key='refresh_overview', icon=':material/refresh:')
    except APIError as exc:
        st.error(str(exc))
        st.button('Retry overview', key='retry_overview')


@st.fragment
def integration_view(client):
    if not available(client): return
    try:
        value=call(client,'GET','/integration')
        with st.container(border=True):
            st.subheader('Workspace connection')
            a, b, c = st.columns(3)
            a.metric('Database', value['database'])
            b.metric('File storage', value['storage'].upper())
            c.metric('Environment', 'Local demo' if value['mode'] == 'demo' else 'Configured service')
            st.caption(value['note'])
        with st.container(border=True):
            st.subheader('NoCap source')
            source = primary_device(call(client, 'GET', '/devices'), os.getenv('NOCAP_DEVICE_ID'))
            if source:
                st.markdown('**'+source['name']+'**')
                st.caption('Synthetic calibration source · not physical hardware' if source['fixture'] else 'Connected source configuration')
                a, b = st.columns(2)
                a.write('Connection: '+source['connection'])
                b.write('Last contact: '+short_time(source['last_seen']))
                with st.expander('Source details'):
                    st.text('Source ID: '+source['id'])
                    st.text('Location: '+(source['location'] or 'Not reported'))
                    st.text('Signing key: '+('Enrolled' if source['public_key'] else 'Not configured'))
                    st.caption('A heartbeat confirms transport, not hardware authenticity.')
            else:
                st.caption('Your NoCap device is not configured for this workspace. Ask the administrator to connect the source.')
        with st.expander('Service readiness'):
            st.dataframe([{'Integration': 'Database query', 'Status': value['database_query']}, {'Integration': 'Signing adapter', 'Status': 'Configured' if value['signing_configured'] else 'Not configured'}, {'Integration': 'Citation verifier', 'Status': 'Configured' if value['verifier_configured'] else 'Prepared fixtures only' if value['mode'] == 'demo' else 'Not configured'}, {'Integration': 'AWS / physical device acceptance', 'Status': 'Not verified'}], hide_index=True, use_container_width=True)
        st.download_button('Download integration status',json.dumps(value,indent=2),'nocap-integration-status.json','application/json',on_click='ignore')
        st.button('Refresh connection status')
        with st.expander('Configuration boundary'):
            st.write('Only the backend reads DATABASE_URL, S3_BUCKET, and its IAM role. Devices use scoped upload tokens. The dashboard uses a server-side workspace token. See docs/FULLSTACK.md for migrations, TLS, signing adapter contracts and production cutover.')
    except APIError as exc: st.error(str(exc));st.button('Retry connection',key='retry_integration')
