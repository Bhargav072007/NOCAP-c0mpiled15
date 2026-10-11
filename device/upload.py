"""Device-side HTTPS transport; reads a record signed by the owner's module.
No database/S3 credentials. Retries preserve the exact capture ID and bytes.
"""
import argparse,hashlib,json,os,time
from pathlib import Path
from urllib.parse import urlparse
import requests

def upload(base_url,token,record_path,file_path,allow_local=False):
    parsed=urlparse(base_url)
    if parsed.scheme!='https' and not (allow_local and parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1','::1'}):
        raise ValueError('HTTPS required; allow-local permits loopback demo only')
    if parsed.username or parsed.password: raise ValueError('Credentials must not be embedded in URL')
    record=json.loads(Path(record_path).read_text());path=Path(file_path)
    if not 0<path.stat().st_size<=25*1024*1024: raise ValueError('File must contain 1 byte to 25 MiB')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=record['file_sha256']: raise ValueError('File digest does not match signed record')
    headers={'Authorization':'Bearer '+token}
    with requests.Session() as session:
        heartbeat=session.post(base_url.rstrip('/')+'/devices/'+record['device_id']+'/heartbeat',json={'firmware':'nocap-transport/0.2'},headers=headers,timeout=(3.05,20),allow_redirects=False)
        if heartbeat.status_code!=200: raise RuntimeError(f'Heartbeat rejected: HTTP {heartbeat.status_code}')
        for attempt in range(3):
            try:
                response=session.post(base_url.rstrip('/')+'/captures',headers=headers,files={'file':(record['file_name'],data)},data={'record':json.dumps(record)},timeout=(3.05,30),allow_redirects=False)
                if response.status_code in {200,201}: return response.json()
                if response.status_code not in {502,503,504}: raise RuntimeError(f'Capture rejected: HTTP {response.status_code}; reconcile record/chain before retry')
            except requests.RequestException:
                pass
            if attempt<2: time.sleep(2**attempt)
    raise RuntimeError('Upload outcome unknown; retry the same immutable record ID after checking connectivity')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',required=True);p.add_argument('--file',required=True);p.add_argument('--allow-local',action='store_true');a=p.parse_args()
    print(json.dumps(upload(os.environ['NOCAP_API'],os.environ['NOCAP_DEVICE_TOKEN'],a.record,a.file,a.allow_local)))
