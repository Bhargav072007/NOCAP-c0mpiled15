"""Explicit fixture/live adapters. Transport failure never changes data mode."""
import hashlib
import json
import os
import re
from urllib.parse import urlparse
import requests
from ledger.merkle import merkle_root

HEX64 = re.compile(r'^[0-9a-fA-F]{64}$')
TX = re.compile(r'^0x[0-9a-fA-F]{64}$')

class APIError(Exception):
    """Safe message suitable for display; never include request headers/secrets."""


def validate_ledger(value):
    if not isinstance(value, dict) or not isinstance(value.get('records'), list):
        raise APIError('Malformed ledger: expected an object with a records list.')
    if 'merkle_root' not in value or 'anchor_tx' not in value:
        raise APIError('Malformed ledger: merkle_root or anchor_tx is missing.')
    if value['merkle_root'] is not None and not (
        isinstance(value['merkle_root'], str) and HEX64.fullmatch(value['merkle_root'])
    ):
        raise APIError('Malformed ledger: expected a SHA-256 root or null.')
    if any(not isinstance(r, dict) or not isinstance(r.get('record_hash'), str)
           or not HEX64.fullmatch(r['record_hash']) for r in value['records']):
        raise APIError('Malformed ledger: records must contain SHA-256 record_hash values.')
    if 'chain_ok' in value and value['chain_ok'] is not None and type(value['chain_ok']) is not bool:
        raise APIError('Malformed ledger: chain_ok must be boolean or null.')
    if 'chain_msg' in value and not isinstance(value['chain_msg'], str):
        raise APIError('Malformed ledger: chain_msg must be text.')
    if value['anchor_tx'] is not None and not (
        isinstance(value['anchor_tx'], str) and TX.fullmatch(value['anchor_tx'])
    ):
        raise APIError('Malformed ledger: anchor_tx must be a transaction hash or null.')
    return value


def export_ledger(value):
    """Serialize the received object without adding an integrity claim."""
    validate_ledger(value)
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8')


def explorer_url(tx):
    return f'https://sepolia.etherscan.io/tx/{tx}' if isinstance(tx, str) and TX.fullmatch(tx) else None


class LiveClient:
    mode = 'live'

    def __init__(self, base_url, session=None, token=None):
        parsed = urlparse(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
            raise APIError('NOCAP_API must be an HTTP(S) URL without embedded credentials.')
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.token = token if token is not None else os.getenv('NOCAP_TOKEN','')
        self.demo = os.getenv('NOCAP_SERVICE_DEMO')=='1'
        if self.token and parsed.scheme!='https' and parsed.hostname not in {'localhost','127.0.0.1','::1'}:
            raise APIError('Authenticated APIs require HTTPS outside loopback.')

    def request(self, method, path, **kwargs):
        if self.token:
            kwargs['headers'] = {**kwargs.get('headers',{}), 'Authorization':'Bearer '+self.token}
        try:
            response = self.session.request(method, self.base_url + path,
                                            timeout=kwargs.pop('timeout', (3.05, 20)), allow_redirects=False, **kwargs)
            if not 200 <= response.status_code < 300:
                hint={401:'Sign in again or check the access token.',403:'Your role does not permit this action.',409:'This record changed or already exists. Refresh before saving.',413:'The file or snapshot exceeds the supported size limit.',422:'Check required fields and the submitted record.',503:'The required service or integration is unavailable.'}.get(response.status_code,'Check the service and retry.')
                raise APIError(f'API returned HTTP {response.status_code}. {hint}')
            return response
        except requests.RequestException:
            raise APIError('API disconnected or timed out. Check NOCAP_API and the service, then retry.') from None

    def json(self, method, path, **kwargs):
        try:
            return self.request(method, path, **kwargs).json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            raise APIError('Malformed response: API did not return valid JSON.') from None

    def ledger(self):
        return validate_ledger(self.json('GET', '/ledger'))

    def captures(self, after=0):
        return validate_captures(self.json('GET', '/captures', params={'after':after,'limit':100}))

    def capture_file(self, capture_id):
        response = self.request('GET', '/captures/' + quote(capture_id, safe='') + '/file', stream=True)
        data = bytearray()
        try:
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > MAX_FILE:
                    raise APIError('Capture exceeds the 25 MiB preview limit.')
        except requests.RequestException:
            raise APIError('Capture download interrupted. Retry the preview.') from None
        finally:
            response.close()
        return bytes(data)

    def verify_file(self, name, data, mime='application/octet-stream'):
        if not data or len(data) > MAX_FILE:
            raise APIError('Choose a nonempty file up to 25 MiB.')
        return validate_verdict(self.json('POST', '/verify/file', files={'file': (name, data, mime)}))

    def report(self, text, capture_ids=None, mode='configured'):
        if not text.strip() or len(text) > 50000:
            raise APIError('Enter between 1 and 50,000 characters.')
        return validate_report(self.json('POST', '/reports', json={'text':text, 'capture_ids':capture_ids or [], **({'mode':mode} if mode!='configured' else {})}, timeout=(3.05,600)))

    def report_file(self, name, data, mime='application/octet-stream', capture_ids=None, mode='configured'):
        if not data or len(data)>MAX_FILE:
            raise APIError('Choose a nonempty manuscript up to 25 MiB.')
        return validate_report(self.json('POST','/reports/file',
            files={'file':(name,data,mime)}, data={'capture_ids':json.dumps(capture_ids or []),'mode':mode},
            timeout=(3.05,600)))

    def reports(self):
        return self.json('GET','/reports')

    def saved_report(self, report_id):
        return validate_report(self.json('GET','/reports/'+quote(report_id,safe='')))

    def anchor(self):
        # Contract stays POST /ledger/anchor with no invented request fields.
        value=self.json('POST','/ledger/anchor')
        if not isinstance(value,dict) or not isinstance(value.get('tx_hash'),str) or not TX.fullmatch(value['tx_hash']):
            raise APIError('Malformed anchor response: transaction hash missing.')
        if value.get('explorer_url')!=explorer_url(value['tx_hash']):
            raise APIError('Anchor response must link to the exact Sepolia transaction.')
        if 'merkle_root' in value and not (isinstance(value['merkle_root'],str) and HEX64.fullmatch(value['merkle_root'])):
            raise APIError('Malformed anchor response root.')
        return value


class FixtureClient:
    mode = 'fixture'

    def __init__(self, scenario='Populated'):
        self.scenario = scenario

    def json(self, method, path, **kwargs):
        raise APIError('Workspace extensions require the full-stack API.')

    def guard(self):
        if self.scenario == 'Disconnected':
            raise APIError('Simulated disconnection. Choose Populated to recover; no live request was sent.')
        if self.scenario == 'Malformed':
            raise APIError('Simulated malformed API response. Choose Populated to recover.')
        if self.scenario == 'Slow':
            import time
            time.sleep(1.5)

    def captures(self):
        self.guard()
        records = json.loads((DEMO / 'captures.json').read_text())
        if self.scenario == 'Empty':
            return []
        if self.scenario == 'Long list':
            records = [dict(records[i % 3], id=f'demo_long_{i}', record_hash=hashlib.sha256(f'long-{i}'.encode()).hexdigest()) for i in range(60)]
        return validate_captures(records)

    def capture_file(self, capture_id):
        records = self.captures()
        record = next((r for r in records if r['id'] == capture_id), None)
        if record is None:
            raise APIError('Capture is not available in this fixture snapshot.')
        return (DEMO / record['file_name']).read_bytes()

    def verify_file(self, name, data, mime='application/octet-stream'):
        self.guard()
        if not data or len(data) > MAX_FILE:
            raise APIError('Choose a nonempty file up to 25 MiB.')
        matched = next((r for r in self.captures() if r['file_sha256'] == hashlib.sha256(data).hexdigest()), None)
        return validate_verdict({'status': 'VERIFIED' if matched else 'CAP',
            'matched_id': matched['id'] if matched else None,
            'reason': 'Synthetic registry hash match; no cryptographic signature verified.' if matched else 'No byte-for-byte match in the synthetic registry. This is a demo verdict, not an authenticity judgment.',
            'fixture': True})

    def report(self, text, capture_ids=None):
        self.guard()
        if self.scenario == 'Empty':
            return {'report_id':'demo-empty','results':[], 'fixture':True}
        if text.strip() == (DEMO / 'paper_real.txt').read_text().strip():
            statuses = ['VERIFIED','MISMATCH','UNSUPPORTED','NOT_FOUND']
            results = [{'citation':f'Demo Reference {chr(65+i)} (fictional)',
                        'claim':line, 'status':status, 'matched_title':'Synthetic example only',
                        'doi':'', 'reason':reason} for i,(line,status,reason) in enumerate(zip(text.strip().splitlines()[1:],statuses,[
                        'Scripted example of a supported claim. No publication lookup ran.',
                        'Scripted mismatch: the supplied synthetic image was altered.',
                        'Scripted review: the fictional source does not establish a universal effect.',
                        'Scripted missing source: this reference is fictional.']))]
        elif text.strip() == (DEMO / 'paper_fake_refs.txt').read_text().strip():
            results = [{'citation':line, 'claim':'Synthetic planted reference', 'status':'NOT_FOUND',
                        'matched_title':'','doi':'','reason':'Planted fictional reference; fixture outcome, no live lookup.'}
                       for line in text.strip().splitlines()[1:]]
        else:
            raise APIError('Fixture mode only supports the prepared synthetic examples. Choose a demo text or configure the live API for other text.')
        return validate_report({'report_id':'demo-'+hashlib.sha256(text.encode()).hexdigest()[:12],
                                'results':results,'fixture':True})

    def ledger(self):
        records = self.captures()
        return validate_ledger({'records': records,
            'merkle_root': merkle_root([r['record_hash'] for r in records]),
            'chain_ok': None, 'chain_msg': 'Not checked: synthetic, unsigned demo records.',
            'anchor_tx': None, 'fixture': True})


def make_client(scenario='Populated'):
    mode = os.getenv('NOCAP_MODE', 'fixture').lower()
    if mode == 'fixture':
        return FixtureClient(scenario)
    if mode == 'live':
        return LiveClient(os.getenv('NOCAP_API', 'http://localhost:8000'))
    raise APIError('NOCAP_MODE must be fixture or live. No automatic fallback is used.')

# P4 contract validation is deliberately separate from the UI.
from pathlib import Path
from urllib.parse import quote
DEMO = Path(__file__).resolve().parents[1] / 'demo'
MAX_FILE = 25 * 1024 * 1024
STATUSES = {'VERIFIED', 'CAP', 'UNSUPPORTED'}
CITATION_STATUSES = {'VERIFIED', 'MISMATCH', 'NOT_FOUND', 'UNSUPPORTED'}


def validate_captures(value):
    if not isinstance(value, list):
        raise APIError('Malformed captures: expected a list of records.')
    seen = set()
    for record in value:
        if not isinstance(record, dict):
            raise APIError('Malformed capture record.')
        for key in ('id','type','file_name','file_sha256','captured_at','device_id','location','prev_hash','record_hash','signature','status'):
            if not isinstance(record.get(key), str):
                raise APIError(f'Malformed capture: {key} must be text.')
        if (record['id'] in seen or not record['id'] or record['status'] not in STATUSES
            or record['type'] not in {'photo','audio','reading'}
            or any(not HEX64.fullmatch(record[k]) for k in ('file_sha256','prev_hash','record_hash'))):
            raise APIError('Malformed capture: invalid ID, type, status or hash.')
        seen.add(record['id'])
    return value


def validate_verdict(value):
    if not isinstance(value, dict) or value.get('status') not in STATUSES:
        raise APIError('Malformed verification: unknown status.')
    if value['status']=='VERIFIED' and not isinstance(value.get('matched_id'), str):
        raise APIError('Malformed verification: VERIFIED requires a matched capture ID.')
    if value['status']=='CAP' and not isinstance(value.get('reason'), str):
        raise APIError('Malformed verification: CAP requires a reason.')
    if 'reason' in value and not isinstance(value['reason'],str):
        raise APIError('Malformed verification: reason must be text.')
    return value


def validate_report(value):
    if not isinstance(value,dict) or not isinstance(value.get('report_id'),str) or not isinstance(value.get('results'),list):
        raise APIError('Malformed citation report.')
    for result in value['results']:
        if not isinstance(result,dict) or result.get('status') not in CITATION_STATUSES:
            raise APIError('Malformed citation report: unknown status.')
        if any(not isinstance(result.get(k),str) for k in ('citation','claim','reason','matched_title','doi')):
            raise APIError('Malformed citation report: missing text fields.')
    return value
