"""Device-side HTTPS transport. Secrets stay in environment/private token files."""
import argparse,hashlib,json,os,time
from pathlib import Path
from urllib.parse import urlparse
import requests


def upload(base_url,token,record_path,file_path,allow_local=False,metadata=None):
    parsed=urlparse(base_url)
    if parsed.scheme!='https' and not (allow_local and parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1','::1'}):
        raise ValueError('HTTPS required; allow-local permits loopback demo only')
    if not parsed.netloc or parsed.username or parsed.password: raise ValueError('Use a host URL without embedded credentials')
    if not token: raise ValueError('A device token is required')
    path=Path(file_path)
    if not 0<path.stat().st_size<=50*1024*1024: raise ValueError('File must contain 1 byte to 50 MiB')
    data=path.read_bytes()
    record=json.loads(Path(record_path).read_text()) if record_path else None
    if record and hashlib.sha256(data).hexdigest()!=record['file_sha256']:
        raise ValueError('File digest does not match signed record')
    if not record and path.suffix.lower() not in {'.jpg','.jpeg','.png','.mp4'}:
        raise ValueError('File-only upload accepts JPEG, PNG and MP4')
    fields={}
    if record: fields['record']=json.dumps(record)
    if metadata is not None: fields['metadata']=json.dumps(metadata)
    headers={'Authorization':'Bearer '+token}
    mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.mp4':'video/mp4'}.get(path.suffix.lower(),'application/octet-stream')
    # The deployed file-only gateway does not expose the workspace heartbeat API.
    # A successful workspace ingest updates last_seen, so no preflight is required.
    with requests.Session() as session:
        attempts=3 if record else 1
        for attempt in range(attempts):
            try:
                response=session.post(base_url.rstrip('/')+'/captures',headers=headers,
                    files={'file':(record['file_name'] if record else path.name,data,mime)},
                    data=fields,timeout=(5,120),allow_redirects=False)
                if response.status_code in {200,201}:
                    try: receipt=response.json()
                    except ValueError: raise RuntimeError('Upload accepted, but response was not JSON; inspect server before retrying') from None
                    if not isinstance(receipt,dict): raise RuntimeError('Upload receipt must be a JSON object')
                    for field in ('sha256','file_sha256'):
                        if field in receipt and receipt[field]!=hashlib.sha256(data).hexdigest():
                            raise RuntimeError('Server receipt hash does not match the uploaded file; stop and investigate')
                    return receipt
                if response.status_code not in {502,503,504}:
                    raise RuntimeError(f'Capture rejected: HTTP {response.status_code}; inspect source enrollment, format and signed record')
            except requests.RequestException:
                pass
            if attempt<attempts-1: time.sleep(2**attempt)
    raise RuntimeError('Upload outcome unknown; inspect server before retrying. Signed retries must retain the same record ID and bytes.')


def device_token():
    path=os.getenv('NOCAP_DEVICE_TOKEN_FILE')
    return Path(path).read_text().strip() if path else os.getenv('NOCAP_DEVICE_TOKEN','').strip()


if __name__=='__main__':
    from dotenv import load_dotenv
    load_dotenv()
    p=argparse.ArgumentParser()
    p.add_argument('--record',help='Signed record JSON. Omit only for explicitly unsigned file-only ingestion.')
    p.add_argument('--file',required=True)
    p.add_argument('--metadata',help='JSON file containing label, experiment_id, sample_id and notes')
    p.add_argument('--allow-local',action='store_true')
    a=p.parse_args()
    metadata=json.loads(Path(a.metadata).read_text()) if a.metadata else None
    print(json.dumps(upload(os.environ['NOCAP_API'],device_token(),a.record,a.file,a.allow_local,metadata)))
