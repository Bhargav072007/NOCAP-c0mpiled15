"""Synthetic local transport rehearsal. Does not emulate signatures or physical hardware."""
from pathlib import Path
import sys,uuid,json,hashlib
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
import requests
from device.upload import upload

if __name__=='__main__':
    config=dotenv_values('.runtime/local.env');base=config['NOCAP_API']
    if base not in {'http://127.0.0.1:8000','http://localhost:8000'}: raise SystemExit('Simulator is restricted to the local demo API')
    response=requests.post(base+'/devices',headers={'Authorization':'Bearer '+config['NOCAP_TOKEN']},json={'name':'Synthetic NoCap transport','location':'Local software simulator'},timeout=10)
    response.raise_for_status();device=response.json();data=Path('demo/photo.jpg').read_bytes()
    record={'id':'sim_'+uuid.uuid4().hex[:20],'type':'photo','file_name':'synthetic-transport.jpg','file_sha256':hashlib.sha256(data).hexdigest(),'captured_at':datetime.now(timezone.utc).isoformat(),'device_id':device['id'],'location':'Local software simulator','prev_hash':'0'*64,'record_hash':hashlib.sha256(uuid.uuid4().bytes).hexdigest(),'signature':''}
    path=Path('.runtime/simulator-record.json');path.write_text(json.dumps(record))
    result=upload(base,device['token'],path,'demo/photo.jpg',allow_local=True)
    print(json.dumps({'capture':result,'device_id':device['id'],'coverage':'Local HTTP transport and storage only; unsigned synthetic record.'},indent=2))
