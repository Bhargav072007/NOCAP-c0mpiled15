"""Explicit local demo seed. Never run automatically against RDS."""
from pathlib import Path
import json,os,secrets
from sqlalchemy import select,insert
from cloud.config import Settings
from cloud import db
from cloud.storage import storage_for
from cloud.api import digest,now


def initialize(settings,token):
    if not settings.demo or not settings.database_url.startswith('sqlite:'):
        raise ValueError('Demo bootstrap is restricted to explicit local SQLite mode')
    engine=db.engine_for(settings);db.metadata.create_all(engine);store=storage_for(settings)
    with engine.begin() as conn:
        if conn.execute(select(db.orgs.c.id).where(db.orgs.c.id=='org_demo')).first(): return
        conn.execute(insert(db.orgs).values(id='org_demo',name='NoCap / Engineering'))
        names=[('mem_divyam','Divyam','admin','Ledger & dashboard'),('mem_bhargav','Bhargav','reviewer','Integration'),('mem_avishkar','Avishkar','collaborator','Cloud'),('mem_pranav','Pranav','collaborator','Device & verifier'),('mem_sanjay','Sanjay','reviewer','Signing')]
        for id,name,role,area in names:
            conn.execute(insert(db.members).values(id=id,org_id='org_demo',name=name,email=name.lower()+'@example.test',role=role,active=True))
        conn.execute(insert(db.tokens).values(digest=digest(token),org_id='org_demo',member_id='mem_divyam',revoked=False))
        root=Path(__file__).resolve().parents[1]
        records=json.loads((root/'demo/captures.json').read_text())
        for device in sorted({r['device_id'] for r in records}):
            conn.execute(insert(db.devices).values(id=device,org_id='org_demo',name='Synthetic calibration source',location='Demo workspace',public_key='',enabled=True,fixture=True,last_hash='0'*64))
        for r in records:
            key='org_demo/seed_'+r['id']
            try: store.put(key,(root/'demo'/r['file_name']).read_bytes())
            except FileExistsError: pass
            conn.execute(insert(db.captures).values(org_id='org_demo',id=r['id'],device_id=r['device_id'],file_sha256=r['file_sha256'],record_hash=r['record_hash'],payload=r,object_key=key,created_at=now()))
        tasks=[('work_sources','Review source provenance','Methods','mem_sanjay','In progress','High','demo_1'),('work_citations','Resolve unsupported references','Literature review','mem_pranav','To review','High',None),('work_cloud','Validate device-to-cloud handoff','Data collection','mem_avishkar','To review','Normal',None),('work_export','Check the final evidence export','Appendix','mem_divyam','Changes requested','Normal',None)]
        for id,title,section,owner,status,priority,capture in tasks:
            conn.execute(insert(db.work).values(id=id,org_id='org_demo',title=title,section=section,owner_id=owner,status=status,priority=priority,capture_id=capture,version=1,created_at=now(),updated_at=now()))
        conn.execute(insert(db.audit).values(org_id='org_demo',actor='mem_divyam',action='demo.workspace_seeded',target='org_demo',created_at=now()))
    engine.dispose()

if __name__=='__main__':
    from dotenv import load_dotenv
    load_dotenv()
    path=Path('.runtime/local.env');path.parent.mkdir(exist_ok=True)
    if path.exists():
        from dotenv import dotenv_values
        token=dotenv_values(path)['NOCAP_TOKEN']
    else:
        token=secrets.token_urlsafe(32)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:
            f.write('NOCAP_MODE=live\nNOCAP_API=http://127.0.0.1:8000\nNOCAP_SERVICE_DEMO=1\nNOCAP_BACKEND_MODE=demo\nNOCAP_TOKEN='+token+'\n')
    initialize(Settings.env(),token)
    print('Local workspace initialized. Server-only settings: .runtime/local.env (0600). No AWS calls made.')
