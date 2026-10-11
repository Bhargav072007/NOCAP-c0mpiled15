"""Bounded external requests. Errors carry no response bodies or credentials."""
import ipaddress
import os
import socket
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DependencyError(RuntimeError): pass

_session = requests.Session()
_session.mount('https://', HTTPAdapter(max_retries=Retry(total=2, backoff_factor=.5,
    status_forcelist=[429,500,502,503,504], allowed_methods=['GET'], respect_retry_after_header=False)))

def request_json(url, params=None, headers=None, *, data=None):
    contact = os.getenv('NOCAP_CONTACT_EMAIL','')
    base = {'User-Agent':'NoCap/0.2'+(f' (mailto:{contact})' if contact else '')}
    try:
        response = _session.request('POST' if data is not None else 'GET', url, params=params,
            data=data, headers=base | (headers or {}), timeout=(5,20), allow_redirects=False)
        if response.status_code == 404: return None
        response.raise_for_status()
        if 300 <= response.status_code < 400: raise ValueError('unexpected redirect')
        return response.json()
    except (requests.RequestException,ValueError) as exc:
        raise DependencyError('External service unavailable, denied access or returned invalid data') from exc

def get_json(url, params=None, headers=None):
    payload = request_json(url,params,headers)
    if payload is not None and not isinstance(payload,dict):
        raise DependencyError('External service returned invalid object')
    return payload

def validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise DependencyError('Full-text URL must be public HTTPS without credentials')
    try:
        addresses = socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
            raise DependencyError('Private/non-public full-text destination refused')
    except (socket.gaierror,ValueError) as exc:
        raise DependencyError('Full-text destination unavailable') from exc

def get_bytes(url, params=None, *, max_bytes=20_000_000):
    """Stream a bounded document, validate each redirect, never send provider tokens."""
    try:
        for _ in range(5):
            validate_public_url(url)
            with _session.get(url,params=params,timeout=(5,20),stream=True,allow_redirects=False,
                              headers={'User-Agent':'NoCap/0.2'}) as response:
                if 300 <= response.status_code < 400:
                    url=urljoin(url,response.headers.get('Location',''));params=None;continue
                response.raise_for_status()
                chunks=[];size=0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > max_bytes: raise DependencyError('Source exceeds download size limit')
                    chunks.append(chunk)
                return b''.join(chunks),response.headers.get('Content-Type',''),url
        raise DependencyError('Too many full-text redirects')
    except (requests.RequestException,ValueError) as exc:
        raise DependencyError('Full text unavailable or invalid') from exc
