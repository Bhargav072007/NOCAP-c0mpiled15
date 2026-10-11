"""Shared presentation. All untrusted values are escaped before custom HTML."""
from html import escape
from pathlib import Path
import streamlit as st
from dashboard.client import APIError, export_ledger, explorer_url


def styles(opaque=False, still=False):
    css = Path(__file__).with_name('fonts.css').read_text()
    css += Path(__file__).with_name('style.css').read_text()
    css += Path(__file__).with_name('motion.css').read_text()
    css += Path(__file__).with_name('demo.css').read_text()
    css += Path(__file__).with_name('refinement.css').read_text()
    css += Path(__file__).with_name('lively.css').read_text()
    css += Path(__file__).with_name('product.css').read_text()
    if opaque:
        css += '.nc-mode-banner,.nc-status {background:#141a10!important;}'
    if still:
        css += '''.st-key-public *,.st-key-public *::before,.st-key-public *::after,
          .st-key-login *,.st-key-login *::before,.st-key-login *::after,
          .st-key-workspace,.st-key-workspace *,.st-key-workspace *::before,.st-key-workspace *::after,
          .st-key-sidebar_nav *,.st-key-sidebar_nav *::before,.st-key-sidebar_nav *::after
          {animation:none!important;transition:none!important;}
          .nc-hero-line>span{transform:none!important;opacity:1!important;}
          [role=dialog]{transition:none!important;transform:none!important;}
          @starting-style{[role=dialog]{opacity:1!important;transform:none!important;}}
          .nc-ambient-control,.nc-ambient-checkbox,.nc-demo-pause,#nc-demo-pause,.nc-motion-toggle{display:none;}
          .nc-flow-scan{display:none;}'''
    st.html('<style>' + css + '</style>')


def badge(status, fixture=False, event=None, token=None, cached=False):
    reveal = False
    if event is not None:
        cache = st.session_state.setdefault('motion_events', {})
        reveal = cache.get(event) != token
        cache[event] = token
    color = {'VERIFIED':'good','CAP':'bad','NOT_FOUND':'bad','MISMATCH':'review','UNSUPPORTED':'review'}.get(status,'neutral')
    label = ('DEMO · ' if fixture else 'CACHED · ' if cached else '') + status
    st.html(f'<span class="nc-badge {color} {"nc-reveal" if reveal else ""}">{escape(label)}</span>')


def empty(title, detail):
    st.html(f'<div class="nc-state"><strong>{escape(title)}</strong><p>{escape(detail)}</p></div>')


@st.fragment
def ledger_view(client):
    with st.container(key='ledger_panel'):
        st.html('<div class="nc-panel-label">AUDIT LEDGER</div>')
        st.subheader('Audit ledger')
        st.caption('Inspect the source snapshot. Export an audit trail you can take with you.')
        st.button('Refresh ledger', key='refresh_ledger', icon=':material/refresh:')
        try:
            with st.spinner('Loading the ledger snapshot…'):
                led = client.ledger()
        except APIError as exc:
            st.error(str(exc))
            return
        if client.mode!='fixture' and led.get('fixture'):
            st.info('API supplied synthetic fixture data; no live verification is established.')
        elif led.get('cached'):
            st.info('Cached API snapshot; no fresh verification is implied.')
        a,b,c = st.columns(3)
        a.metric('Records in snapshot', len(led['records']))
        b.metric('Signed records supplied', sum(bool(r.get('signature')) for r in led['records']))
        c.metric('Chain status', {True:'API: intact',False:'API: broken',None:'Not checked'}[led.get('chain_ok')])
        st.caption(led.get('chain_msg', 'The API did not supply a chain verification result.'))
        if not led['records']:
            empty('No records yet', 'Once captures are available, their ordered hashes will form the ledger root.')
        st.markdown('##### Merkle root')
        previous = st.session_state.get('displayed_root')
        if previous != led['merkle_root']:
            st.html('<div class="nc-root-update">Snapshot root received</div>')
        st.session_state.displayed_root = led['merkle_root']
        st.code(led['merkle_root'] or 'No Merkle root — empty snapshot', language=None)
        st.caption('SHA-256 · ordered record hashes · odd leaves duplicated. This root alone does not verify signatures.')
        with st.expander('Inspect the records and full hashes'):
            for i, record in enumerate(led['records'],1):
                st.html(f'<div class="nc-record"><span>{i:02d} · {escape(str(record.get("id","Unnamed record")))}</span><code>{escape(record["record_hash"])}</code></div>')
            st.json(led, expanded=False)
        if url := explorer_url(led.get('anchor_tx')):
            st.link_button('View submitted transaction on Sepolia', url)
            st.caption('Confirmation and matching snapshot association have not been checked.')
        st.download_button('Download ledger JSON', export_ledger(led), 'nocap_ledger.json',
                           'application/json', on_click='ignore', key='ledger_download', type='primary', icon=':material/download:')
        st.caption('Exports this exact response as nocap_ledger.json. No extra integrity claims are added.')
        anchor_controls(client,led)


def captures_view(client):
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO
    with st.container(key='capture_panel'):
        st.html('<div class="nc-panel-label">CAPTURE REGISTRY</div>')
        st.subheader('Original captures')
        st.caption('Inspect the original file, source metadata, and the API’s returned verdict.')
        st.button('Refresh captures', key='refresh_captures', icon=':material/refresh:')
        try:
            with st.spinner('Loading capture records…'):
                paged=getattr(client,'workspace_extensions',False)
                cursors=st.session_state.setdefault('capture_cursors',[0])
                records = client.captures(after=cursors[-1]) if paged else client.captures()
        except APIError as exc:
            st.error(str(exc))
            return
        if paged:
            prev,next_=st.columns(2)
            if len(cursors) > 1 and prev.button('Previous capture page'):
                cursors.pop();st.rerun()
            if len(records) >= 100 and next_.button('Next capture page'):
                cursors.append(records[-1]['sequence']);st.rerun()
            if len(cursors) > 1: st.caption('Capture page '+str(len(cursors)))
        if not records:
            empty('The trail starts here', 'No captures in this snapshot. Refresh after a capture reaches the API.')
            return
        ordered = list(reversed(records))
        ids = [r['id'] for r in ordered]
        if st.session_state.get('capture_selection') not in ids:
            # Start with the photo to make the synthetic provenance clear.
            st.session_state.capture_selection = next((r['id'] for r in ordered if r['type']=='photo'),ids[0])
        lookup = {r['id']:r for r in ordered}
        selected = st.selectbox('Select capture', ids, key='capture_selection',
            format_func=lambda id: f"{lookup[id]['type'].upper()} · {lookup[id]['file_name']} · {id}")
        record=lookup[selected]
        left,right=st.columns([1.3,1], gap='large')
        with left:
            try:
                cache = st.session_state.setdefault('preview_cache',{})
                key = (selected,record['file_sha256'])
                if key not in cache:
                    with st.spinner('Loading original file…'):
                        cache.clear()  # bound session memory to one file
                        cache[key]=client.capture_file(selected)
                data=cache[key]
                if record['type']=='photo':
                    image = Image.open(BytesIO(data))
                    image.verify()
                    st.image(data, caption='Synthetic calibration graphic · not a camera capture' if client.mode=='fixture' else record['file_name'], width='stretch')
                elif record['type']=='video':
                    st.video(data,format='video/mp4')
                    st.caption('Original video. File integrity is separate from scientific content review.')
                elif record['type']=='audio':
                    st.audio(data)
                    st.caption('Synthetic 440 Hz tone · not a field recording' if client.mode=='fixture' else 'Original API audio')
                else:
                    st.code(data.decode('utf-8',errors='replace'),language='json')
                st.download_button('Download original file',data,record['file_name'],on_click='ignore',key='original_download')
            except (APIError,UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
                st.error(str(exc) if isinstance(exc,APIError) else 'Preview unavailable: the API file is not a supported image.')
        with right:
            badge(record['status'],client.mode=='fixture' or bool(record.get('fixture')), 'capture', record['id']+record['record_hash'], bool(record.get('cached')))
            st.markdown('### '+record['file_name'].replace('`',''))
            st.caption(record.get('reason','Verdict supplied by the API; dashboard did not verify signatures.'))
            st.text(f"Captured: {record['captured_at']}\nDevice: {record['device_id']}\nLocation: {record['location']}")
            if any(record.get('metadata',{}).values()):
                st.caption('Lab annotations · not covered by the device signature')
                for field,value in record['metadata'].items():
                    if value: st.text(field.replace('_',' ').title()+': '+value)
            if record.get('media'):
                st.caption('Media inspection');st.json(record['media'],expanded=False)
            with st.expander('Full hashes and signature',expanded=False):
                st.caption('File SHA-256'); st.code(record['file_sha256'],language=None)
                st.caption('Record hash'); st.code(record['record_hash'],language=None)
                st.caption('Signature'); st.code(record['signature'] or 'No signature supplied',language=None)
        st.caption(f'{len(records)} records · newest first in selector · stable IDs retained across refresh')


@st.fragment
def verify_view(client):
    import hashlib
    from dashboard.client import DEMO
    with st.container(key='verify_panel'):
        st.html('<div class="nc-panel-label">FILE VERIFICATION</div>')
        st.subheader('Compare a file')
        st.caption('Compare file bytes with the capture registry. A match is the API’s verdict, not a broader authenticity guarantee.')
        if client.mode=='fixture' or getattr(client,'demo',False):
            with st.expander('Get the synthetic demo files'):
                st.caption('Both files are generated calibration graphics. The edited copy changes a color patch; it is not AI generated despite the build-plan filename.')
                for name,label in [('photo.jpg','Download synthetic original'),('photo_ai_edited.jpg','Download synthetic edited copy')]:
                    st.download_button(label,(DEMO/name).read_bytes(),name,'image/jpeg',on_click='ignore')
        with st.form('verify_form'):
            upload = st.file_uploader('Choose a photo or recording',type=['jpg','jpeg','png','webp','wav','mp3','m4a','ogg'],key='verify_upload')
            submitted=st.form_submit_button('Verify file',type='primary',key='verify_submit',icon=':material/fingerprint:')
        if submitted:
            if upload is None:
                st.warning('Choose a file before requesting verification.')
            else:
                fingerprint=hashlib.sha256(upload.getvalue()).hexdigest()
                if st.session_state.get('verified_fingerprint') != fingerprint:
                    st.session_state.pop('verify_result',None)
                    try:
                        with st.spinner('Waiting for the verification response…'):
                            result=client.verify_file(upload.name,upload.getvalue(),upload.type)
                        st.session_state.verify_result=result
                        st.session_state.verified_fingerprint=fingerprint
                        st.session_state.verified_filename=upload.name
                    except APIError as exc:
                        st.error(str(exc))
        result=st.session_state.get('verify_result')
        if result:
            st.caption('Last submitted file: '+st.session_state.get('verified_filename','uploaded file'))
            badge(result['status'],client.mode=='fixture' or bool(result.get('fixture')), 'verification', st.session_state.verified_fingerprint, bool(result.get('cached')))
            st.write(result.get('reason','Verdict supplied by the API.'))
            if result.get('matched_id'): st.code(result['matched_id'],language=None)
            with st.expander('Submitted file SHA-256'):
                st.code(st.session_state.verified_fingerprint,language=None)
            st.caption('Result for the last submitted file above. Selecting a different file does not submit it. Repeated identical submissions reuse this session response; browser reload starts a new check.')
        else:
            empty('Ready when you are', 'Choose a file above to request a verdict. Nothing is submitted until you select Verify file.')



@st.fragment
def citation_view(client):
    import hashlib
    import json
    from dashboard.client import DEMO
    fixture=client.mode=='fixture'
    modes={'Offline evidence checks':'offline'}
    captures=[]
    if not fixture:
        try:
            integration=client.json('GET','/integration')
            if integration.get('hybrid_enabled'):
                modes['Full research analysis · configured provider']='hybrid'
            if getattr(client,'demo',False): modes['Synthetic example · no analysis']='demo'
            captures=client.captures()
        except APIError as exc:
            st.error(str(exc))
            return
    with st.container(key='citation_panel'):
        st.html('<div class="nc-panel-label">RESEARCH REVIEW</div>')
        st.subheader('Make every reference count.')
        st.caption('Connect the manuscript to its evidence. Inspect each finding and keep the full review record.')
        if fixture:
            mode='demo'
        else:
            choice=st.selectbox('Analysis mode',list(modes),key='analysis_mode_choice')
            mode=modes[choice]
        if mode=='demo':
            st.caption('Prepared fictional references only. No publication lookup or model analysis runs.')
            col1,col2=st.columns(2)
            if col1.button('Load mixed demo',key='mixed_demo'):
                st.session_state.report_text=(DEMO/'paper_real.txt').read_text()
            if col2.button('Load three fake references',key='fake_demo'):
                st.session_state.report_text=(DEMO/'paper_fake_refs.txt').read_text()
        elif mode=='offline':
            st.caption('Runs the real local verifier. Checks linked capture integrity and extracts references; source discovery and scientific model review require full analysis.')
        else:
            st.info('Full analysis sends manuscript and relevant evidence to the server’s configured model provider and publication services. It may take several minutes. Human review remains required.')
        with st.form('citation_form'):
            text=st.text_area('Research text',key='report_text',height=180,max_chars=50000,
                              placeholder='Paste the passage and its references…')
            upload=None
            if not fixture and mode!='demo':
                upload=st.file_uploader('Or upload a manuscript',type=['pdf','docx','txt','md','tex'],
                    key='manuscript_upload',help='An uploaded manuscript takes precedence over pasted text. Up to 25 MiB and 50,000 extracted characters. Scanned PDFs need OCR.')
            selected=[]
            if not fixture and mode!='demo':
                labels={r['id']:f"{r['file_name']} · {r['id']}" for r in captures}
                selected=st.multiselect('Link workspace evidence',list(labels),format_func=labels.get,
                    help='Only captures in your organization are available. The API rechecks the complete chain for each selected source.')
            submitted=st.form_submit_button('Check citations',key='citation_submit',type='primary',icon=':material/fact_check:')
        data=upload.getvalue() if upload else text.encode()
        fingerprint=hashlib.sha256(data+json.dumps([mode,selected,upload.name if upload else None]).encode()).hexdigest()
        if submitted:
            if not data.strip():
                st.warning('Add research text or a manuscript before checking citations.')
            elif st.session_state.get('reported_fingerprint')!=fingerprint or st.session_state.get('report_source')=='saved':
                st.session_state.pop('report_result',None)
                try:
                    with st.spinner('Reviewing the manuscript and evidence…'):
                        if upload:
                            result=client.report_file(upload.name,data,upload.type,selected,mode)
                        elif fixture:
                            result=client.report(text,[])
                        else:
                            result=client.report(text,selected,mode=mode)
                    st.session_state.report_result=result
                    st.session_state.reported_fingerprint=fingerprint
                    st.session_state.report_source='current'
                except APIError as exc:
                    st.error(str(exc))
                    if not fixture: st.caption('If a long request timed out, check saved reports before submitting again.')
        if not fixture:
            with st.expander('Saved research reports'):
                try:
                    history=client.reports()
                    if history:
                        names={r['report_id']:f"{r['created_at']} · {r['analysis_mode']} · {r['findings']} findings · {r['report_id'][-6:]}" for r in history}
                        saved=st.selectbox('Choose a saved report',list(names),format_func=names.get)
                        if st.button('Open saved report'):
                            st.session_state.report_result=client.saved_report(saved)
                            st.session_state.report_source='saved'
                    else: st.caption('Completed reports will appear here.')
                except APIError as exc: st.error(str(exc))
        result=st.session_state.get('report_result')
        if result and (st.session_state.get('reported_fingerprint')==fingerprint or st.session_state.get('report_source')=='saved'):
            st.caption(f"Report {result['report_id']} · {result.get('analysis_mode','demo' if fixture else 'configured')} · {len(result['results'])} findings")
            if st.session_state.get('report_source')=='saved': st.caption('Showing a saved report; the form above is a separate submission.')
            analysis=result.get('analysis',{})
            if result.get('evidence_contains_demo'): st.warning('This report includes synthetic workspace captures. Their provenance is not real hardware evidence.')
            if analysis.get('issues'):
                with st.expander('Coverage and review requirements',expanded=True):
                    for issue in analysis['issues']: st.write('• '+issue)
            st.download_button('Download full research report',json.dumps(result,indent=2,ensure_ascii=False),
                file_name=result['report_id']+'.json',mime='application/json',key='download_research_report')
            if not result['results']:
                empty('No findings returned', 'Read the coverage notes. An empty findings list does not establish that the text is verified.')
            for i,finding in enumerate(result['results']):
                with st.container(border=True):
                    badge(finding['status'],fixture or bool(result.get('fixture')), f'citation-{i}', result['report_id'], bool(result.get('cached')))
                    if finding.get('backend_status'): st.caption(f"Check {finding.get('check','review')} · {finding['backend_status']}")
                    st.write(finding['citation'])
                    st.write(finding['reason'])
                    with st.expander('Claim and evidence details'):
                        st.caption('Claim');st.write(finding['claim'] or 'No individual claim attached')
                        st.caption('Matched title');st.write(finding['matched_title'] or 'None supplied')
                        st.caption('DOI');st.text(finding['doi'] or 'None supplied')
                        for key in ('evidence','source_evidence','suggested_fix'):
                            if finding.get(key): st.write(finding[key])
            if analysis:
                with st.expander('Complete verifier audit'):
                    st.json(analysis,expanded=False)
        elif not text and not upload:
            empty('Follow the references', 'Paste text or upload a manuscript. Findings appear after submission.')


def anchor_controls(client,led):
    import os
    enabled=client.mode=='live' and os.getenv('NOCAP_ENABLE_ANCHOR')=='1'
    attempt=st.session_state.get('anchor_attempt')
    disabled=not enabled or bool(led.get('fixture')) or bool(led.get('cached')) or not led['merkle_root'] or attempt is not None or bool(led.get('anchor_tx'))
    st.divider()
    st.markdown('##### Optional · Sepolia anchor')
    st.caption('A zero-value testnet transaction can preserve a root. Submission does not mean confirmation.')
    if st.button('Submit snapshot to Sepolia',key='anchor_submit',disabled=disabled,type='primary'):
        # Set before any network I/O so rerenders and repeated clicks cannot send twice.
        st.session_state.anchor_attempt={'root':led['merkle_root'],'state':'in flight'}
        post_started=False
        with st.spinner('Submitting the snapshot through the configured API…'):
            try:
                current=client.ledger()
                if current['merkle_root']!=led['merkle_root']:
                    raise APIError('Ledger changed before submission. Refresh and inspect the latest snapshot.')
                post_started=True
                result=client.anchor()
                st.session_state.anchor_attempt.update(state='submitted',result=result)
            except APIError as exc:
                st.session_state.anchor_attempt.update(state='outcome unknown' if post_started else 'not submitted',error=str(exc))
        st.rerun()
    if not enabled:
        st.caption('Unavailable in fixtures. Live use requires the API owner’s throwaway Sepolia setup and NOCAP_ENABLE_ANCHOR=1. No wallet key belongs in this dashboard.')
    elif led.get('fixture') or led.get('cached'):
        st.caption('Anchoring is unavailable for a fixture or cached API response.')
    elif not led['merkle_root']:
        st.caption('Nothing to anchor: the snapshot is empty.')
    elif led.get('anchor_tx'):
        st.caption('The API already supplies a transaction. Reconcile it before submitting another.')
    attempt=st.session_state.get('anchor_attempt')
    if attempt:
        st.caption('Root displayed at the time of the request')
        st.code(attempt['root'],language=None)
        if attempt['state']=='submitted':
            result=attempt['result']
            st.info('Transaction submitted · confirmation not checked')
            st.link_button('Inspect submitted Sepolia transaction',result['explorer_url'])
            st.code(result['tx_hash'],language=None)
            if result.get('merkle_root')==attempt['root']:
                st.caption('API reports this transaction for the requested root; chain confirmation remains unchecked.')
            elif result.get('merkle_root'):
                st.warning('API returned a different root. This transaction is not shown as anchoring the requested snapshot.')
                st.code(result['merkle_root'],language=None)
            else:
                st.warning('The API did not return the submitted root. Snapshot association is unverified; inspect transaction input on Sepolia.')
        elif attempt.get('error'):
            st.error(attempt['error'])
            if attempt['state']=='not submitted':
                st.warning('No submission was attempted. Inspect the latest snapshot before reloading the workspace to retry.')
            else:
                st.warning('No automatic retry. The API may have submitted a transaction; reconcile its ledger and Sepolia before starting another session.')
