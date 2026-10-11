"""Authenticated, organization-scoped integration API. No implicit migrations/seeding."""
import hashlib
import importlib
import json
import logging
import secrets
import uuid
from datetime import datetime,timezone,timedelta
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Form,Query,Request
from fastapi.responses import Response,JSONResponse
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy import select,insert,update,func,and_
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from pydantic import ValidationError
from cloud import db
from cloud.config import Settings
from cloud.storage import storage_for
from cloud.schemas import MemberIn,DeviceIn,Heartbeat,WorkIn,WorkUpdate,CommentIn,ReportIn,CaptureIn
from ledger.merkle import merkle_root

log=logging.getLogger('nocap')
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def uid(prefix): return prefix+'_'+uuid.uuid4().hex[:20]
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def plugin(path):
    module,name=path.split(':',1)
    return getattr(importlib.import_module(module),name)

class TooLarge(Exception): pass
class BodyLimit:
    def __init__(self,app,limit): self.app,self.limit=app,limit
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        size=0
        async def bounded():
            nonlocal size
            message=await receive();size+=len(message.get('body',b''))
            if size>self.limit: raise TooLarge()
            return message
        try: await self.app(scope,bounded,send)
        except TooLarge: await JSONResponse({'detail':'Upload exceeds request size limit'},413)(scope,receive,send)

def create_app(settings=None,storage=None):
    settings=settings or Settings.env()
    engine=db.engine_for(settings);store=storage or storage_for(settings)
    app=FastAPI(title='NoCap integration API',version='0.2.0',description='Team workbench, device ingestion and evidence boundary. Demo mode is explicit.')
    app.state.engine,app.state.settings,app.state.storage=engine,settings,store
    app.add_middleware(BodyLimit,limit=settings.max_upload+65536)
    security=HTTPBearer(auto_error=False)
    def connection():
        with engine.begin() as conn: yield conn
    def principal(auth:HTTPAuthorizationCredentials|None=Depends(security),conn=Depends(connection)):
        if auth is None: raise HTTPException(401,'Bearer token required')
        row=conn.execute(select(db.tokens).where(db.tokens.c.digest==digest(auth.credentials),db.tokens.c.revoked==False)).mappings().first()
        if not row: raise HTTPException(401,'Invalid or revoked access token')
        p=dict(row)
        if p.get('expires_at') and datetime.fromisoformat(p['expires_at'])<=datetime.now(timezone.utc):
            raise HTTPException(401,'Access token expired')
        if not settings.demo and not p['device_id'] and not p.get('expires_at'):
            raise HTTPException(401,'Expiring member credential required')
        if p['device_id']:
            d=conn.execute(select(db.devices).where(db.devices.c.id==p['device_id'],db.devices.c.org_id==p['org_id'],db.devices.c.enabled==True)).mappings().first()
            if not d: raise HTTPException(401,'Device disabled')
            p.update(role='device',actor=p['device_id'])
        else:
            m=conn.execute(select(db.members).where(db.members.c.id==p['member_id'],db.members.c.org_id==p['org_id'],db.members.c.active==True)).mappings().first()
            if not m: raise HTTPException(401,'Membership unavailable')
            p.update(role=m['role'],actor=m['id'],name=m['name'])
        return p
    def human(p=Depends(principal)):
        if p['role']=='device': raise HTTPException(403,'Device tokens are ingestion-only')
        return p
    def admin(p=Depends(human)):
        if p['role']!='admin': raise HTTPException(403,'Admin role required')
        return p
    def owned(conn,table,id,p):
        row=conn.execute(select(table).where(table.c.id==id,table.c.org_id==p['org_id'])).mappings().first()
        if not row: raise HTTPException(404,'Resource not found')
        return dict(row)
    def event(conn,p,action,target):
        conn.execute(insert(db.audit).values(org_id=p['org_id'],actor=p['actor'],action=action,target=target,created_at=now()))
    @app.exception_handler(IntegrityError)
    async def conflict(request,exc): return JSONResponse({'detail':'Conflicting ID or existing record'},409)
    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request,exc): return JSONResponse({'detail':'Database unavailable; retry later'},503)
    @app.get('/health')
    def health(): return {'status':'ok','mode':'demo' if settings.demo else 'live'}
    @app.get('/me')
    def me(p=Depends(human),conn=Depends(connection)):
        org=conn.execute(select(db.orgs.c.name).where(db.orgs.c.id==p['org_id'])).scalar_one()
        return {'id':p['actor'],'name':p['name'],'role':p['role'],'organization':org,'demo':settings.demo}
    @app.get('/integration')
    def integration(p=Depends(human),conn=Depends(connection)):
        conn.execute(select(1))
        return {'mode':'demo' if settings.demo else 'live','database':'SQLite / local' if engine.dialect.name=='sqlite' else 'PostgreSQL / TLS',
                'storage':settings.storage,'region':settings.region,'database_query':'passed','signing_configured':bool(settings.signing_plugin),
                'verifier_configured':bool(settings.verifier_plugin),'cloud_verified':False,
                'note':'Configuration is not evidence of AWS reachability. Only the database query ran; S3 and real hardware require acceptance tests.'}
    @app.get('/summary')
    def summary(p=Depends(human),conn=Depends(connection)):
        def count(table,*filters):
            return conn.execute(select(func.count()).select_from(table).where(table.c.org_id==p['org_id'],*filters)).scalar_one()
        return {'captures':count(db.captures),'members':count(db.members,db.members.c.active==True),
                'devices':count(db.devices,db.devices.c.enabled==True),'reviews':count(db.work),
                'approved':count(db.work,db.work.c.status=='Approved'),'open_reviews':count(db.work,db.work.c.status!='Approved'),
                'reports':count(db.reports),'fixture':settings.demo}
    @app.get('/members')
    def members(p=Depends(human),conn=Depends(connection)):
        return [dict(r) for r in conn.execute(select(db.members).where(db.members.c.org_id==p['org_id']).order_by(db.members.c.name).limit(500)).mappings()]
    @app.post('/members',status_code=201)
    def add_member(value:MemberIn,p=Depends(admin),conn=Depends(connection)):
        row={'id':uid('mem'),'org_id':p['org_id'],**value.model_dump(),'email':value.email.lower(),'active':True}
        conn.execute(insert(db.members).values(**row));event(conn,p,'member.added',row['id'])
        return row
    @app.get('/work-items')
    def work_items(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),status:str|None=None,p=Depends(human),conn=Depends(connection)):
        query=select(db.work).where(db.work.c.org_id==p['org_id'])
        if status: query=query.where(db.work.c.status==status)
        return [dict(r) for r in conn.execute(query.order_by(db.work.c.created_at.desc(),db.work.c.id).limit(limit).offset(offset)).mappings()]
    @app.post('/work-items',status_code=201)
    def add_work(value:WorkIn,p=Depends(human),conn=Depends(connection)):
        owned(conn,db.members,value.owner_id,p)
        if value.capture_id: owned(conn,db.captures,value.capture_id,p)
        row={'id':uid('work'),'org_id':p['org_id'],**value.model_dump(),'status':'To review','version':1,'created_at':now(),'updated_at':now()}
        conn.execute(insert(db.work).values(**row));event(conn,p,'review.created',row['id']);return row
    @app.patch('/work-items/{id}')
    def edit_work(id:str,value:WorkUpdate,p=Depends(human),conn=Depends(connection)):
        row=owned(conn,db.work,id,p);owned(conn,db.members,value.owner_id,p)
        if p['role']=='collaborator' and (row['owner_id']!=p['actor'] or value.owner_id!=p['actor']): raise HTTPException(403,'Collaborators may update only their own assigned review')
        if value.status=='Approved' and p['role'] not in {'admin','reviewer'}: raise HTTPException(403,'Reviewer role required for approval')
        result=conn.execute(update(db.work).where(db.work.c.id==id,db.work.c.org_id==p['org_id'],db.work.c.version==value.version).values(status=value.status,owner_id=value.owner_id,version=value.version+1,updated_at=now()))
        if result.rowcount!=1: raise HTTPException(409,'Review changed; refresh before saving')
        event(conn,p,'review.'+value.status.lower().replace(' ','_'),id);return owned(conn,db.work,id,p)
    @app.get('/work-items/{id}/comments')
    def get_comments(id:str,p=Depends(human),conn=Depends(connection)):
        owned(conn,db.work,id,p)
        return [dict(r) for r in conn.execute(select(db.comments).where(db.comments.c.org_id==p['org_id'],db.comments.c.work_id==id).order_by(db.comments.c.created_at,db.comments.c.id).limit(500)).mappings()]
    @app.post('/work-items/{id}/comments',status_code=201)
    def comment(id:str,value:CommentIn,p=Depends(human),conn=Depends(connection)):
        owned(conn,db.work,id,p)
        row={'id':uid('comment'),'org_id':p['org_id'],'work_id':id,'author_id':p['actor'],'body':value.body,'created_at':now()}
        conn.execute(insert(db.comments).values(**row));event(conn,p,'comment.added',id);return row
    @app.get('/activity')
    def activity(after:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),p=Depends(human),conn=Depends(connection)):
        return [dict(r) for r in conn.execute(select(db.audit).where(db.audit.c.org_id==p['org_id'],db.audit.c.sequence>after).order_by(db.audit.c.sequence.desc()).limit(limit)).mappings()]
    @app.get('/devices')
    def devices(p=Depends(human),conn=Depends(connection)):
        rows=[dict(r) for r in conn.execute(select(db.devices).where(db.devices.c.org_id==p['org_id']).order_by(db.devices.c.name).limit(500)).mappings()]
        for r in rows:
            r['connection']='Disabled' if not r['enabled'] else 'Never connected'
            if r['enabled'] and r['last_seen']:
                r['connection']='Recent heartbeat' if datetime.fromisoformat(r['last_seen'])>datetime.now(timezone.utc)-timedelta(seconds=90) else 'Offline'
        return rows
    @app.post('/devices',status_code=201)
    def add_device(value:DeviceIn,p=Depends(admin),conn=Depends(connection)):
        row={'id':uid('dev'),'org_id':p['org_id'],**value.model_dump(),'enabled':True,'fixture':settings.demo,'last_hash':'0'*64}
        token=secrets.token_urlsafe(32)
        conn.execute(insert(db.devices).values(**row));conn.execute(insert(db.tokens).values(digest=digest(token),org_id=p['org_id'],device_id=row['id'],revoked=False));event(conn,p,'device.registered',row['id'])
        return {**row,'token':token,'note':'Shown once. Store on the device; never embed in browser code or Git.'}
    @app.post('/devices/{id}/revoke')
    def revoke(id:str,p=Depends(admin),conn=Depends(connection)):
        owned(conn,db.devices,id,p)
        conn.execute(update(db.devices).where(db.devices.c.id==id,db.devices.c.org_id==p['org_id']).values(enabled=False))
        conn.execute(update(db.tokens).where(db.tokens.c.device_id==id,db.tokens.c.org_id==p['org_id']).values(revoked=True));event(conn,p,'device.revoked',id)
        return {'id':id,'enabled':False}
    @app.post('/devices/{id}/heartbeat')
    def heartbeat(id:str,value:Heartbeat,p=Depends(principal),conn=Depends(connection)):
        if p['role']!='device' or p['device_id']!=id: raise HTTPException(403,'Matching device token required')
        conn.execute(update(db.devices).where(db.devices.c.id==id,db.devices.c.org_id==p['org_id']).values(last_seen=now(),firmware=value.firmware))
        return {'id':id,'received_at':now()}
    @app.post('/captures',status_code=201)
    def ingest(file:UploadFile=File(...),record:str=Form(...,max_length=16384),p=Depends(principal),conn=Depends(connection)):
        if p['role']!='device': raise HTTPException(403,'Device token required')
        try: model=CaptureIn.model_validate_json(record)
        except ValidationError: raise HTTPException(422,'Invalid capture record schema') from None
        data=file.file.read(settings.max_upload+1)
        if not data or len(data)>settings.max_upload: raise HTTPException(413,'File must contain 1 byte to 25 MiB')
        r=model.model_dump()
        if r['device_id']!=p['device_id']: raise HTTPException(403,'Record belongs to another device')
        if hashlib.sha256(data).hexdigest()!=r['file_sha256']: raise HTTPException(422,'File SHA-256 mismatch')
        previous=conn.execute(select(db.captures).where(db.captures.c.org_id==p['org_id'],db.captures.c.id==r['id'])).mappings().first()
        if previous:
            original={k:previous['payload'][k] for k in r}
            if original!=r: raise HTTPException(409,'Capture ID is immutable')
            return {'id':r['id'],'status':previous['payload']['status'],'duplicate':True,'fixture':previous['payload'].get('fixture',False)}
        device=owned(conn,db.devices,p['device_id'],p)
        status='UNSUPPORTED'
        if settings.signing_plugin:
            try: valid=plugin(settings.signing_plugin)(r,device['public_key'])
            except Exception: raise HTTPException(503,'Signing verifier unavailable') from None
            if valid is not True: raise HTTPException(422,'Signature or canonical record hash rejected')
            status='VERIFIED'
        elif not settings.demo: raise HTTPException(503,'Signing integration is required before live ingestion')
        # Atomic head comparison serializes each device chain across API workers.
        changed=conn.execute(update(db.devices).where(db.devices.c.id==r['device_id'],db.devices.c.org_id==p['org_id'],db.devices.c.enabled==True,db.devices.c.last_hash==r['prev_hash']).values(last_hash=r['record_hash'],last_seen=now()))
        if changed.rowcount!=1: raise HTTPException(409,'Device chain head changed; reconcile before retry')
        payload={**r,'status':status,'fixture':settings.demo,'reason':'Unsigned local ingestion; signature verification not configured.' if status=='UNSUPPORTED' else 'Record validated by configured signing adapter.'}
        key=f"{p['org_id']}/{uuid.uuid4().hex}"
        commit_started=False
        try:
            store.put(key,data)
            conn.execute(insert(db.captures).values(org_id=p['org_id'],id=r['id'],device_id=r['device_id'],file_sha256=r['file_sha256'],record_hash=r['record_hash'],payload=payload,object_key=key,created_at=now()))
            event(conn,p,'capture.ingested',r['id']);commit_started=True;conn.commit()
        except Exception:
            conn.rollback()
            if commit_started:
                # A lost commit acknowledgement is not proof of rollback. Keep original
                # bytes until a separate connection proves this row was not committed.
                try:
                    with engine.connect() as check:
                        saved=check.execute(select(db.captures.c.object_key).where(db.captures.c.org_id==p['org_id'],db.captures.c.id==r['id'])).scalar()
                    if saved==key: return {'id':r['id'],'status':status,'fixture':settings.demo,'duplicate':True}
                except Exception:
                    log.error('Commit outcome reconciliation required for capture %s',r['id'])
                    raise HTTPException(503,'Commit outcome unknown; retry the same capture ID') from None
            try: store.delete(key)
            except Exception: log.error('Orphan reconciliation required for capture %s',r['id'])
            raise HTTPException(503,'Storage/commit failed; retry the same capture ID') from None
        return {'id':r['id'],'status':status,'fixture':settings.demo}
    @app.get('/captures')
    def list_captures(limit:int=Query(100,ge=1,le=500),after:int=Query(0,ge=0),p=Depends(human),conn=Depends(connection)):
        return [dict(r.payload,sequence=r.sequence) for r in conn.execute(select(db.captures.c.payload,db.captures.c.sequence).where(db.captures.c.org_id==p['org_id'],db.captures.c.sequence>after).order_by(db.captures.c.sequence).limit(limit))]
    @app.get('/captures/{id}/file')
    def original(id:str,p=Depends(human),conn=Depends(connection)):
        row=owned(conn,db.captures,id,p)
        try: data=store.get(row['object_key'])
        except Exception: raise HTTPException(503,'Original file unavailable') from None
        if len(data)>settings.max_upload or hashlib.sha256(data).hexdigest()!=row['file_sha256']: raise HTTPException(503,'Stored file integrity check failed')
        return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="{id}.bin"','Cache-Control':'no-store'})
    @app.post('/verify/file')
    def verify(file:UploadFile=File(...),p=Depends(human),conn=Depends(connection)):
        data=file.file.read(settings.max_upload+1)
        if not data or len(data)>settings.max_upload: raise HTTPException(413,'File must contain 1 byte to 25 MiB')
        row=conn.execute(select(db.captures.c.payload).where(db.captures.c.org_id==p['org_id'],db.captures.c.file_sha256==hashlib.sha256(data).hexdigest()).order_by(db.captures.c.sequence).limit(1)).scalar()
        return {'status':row['status'] if row else 'CAP','matched_id':row['id'] if row else None,'fixture':settings.demo,
                'reason':'Exact stored byte match. Signature status is reported separately by the capture verdict.' if row else 'No matching file in this organization; this alone does not prove manipulation.'}
    @app.post('/reports',status_code=201)
    def report(value:ReportIn,p=Depends(human),conn=Depends(connection)):
        for id in value.capture_ids: owned(conn,db.captures,id,p)
        if settings.verifier_plugin:
            try:
                from dashboard.client import validate_report
                result=validate_report({'report_id':uid('report'),'results':plugin(settings.verifier_plugin)(value.text)})
            except Exception: raise HTTPException(503,'Citation verifier unavailable or returned invalid results') from None
        elif settings.demo:
            from dashboard.client import FixtureClient,APIError
            try: result=FixtureClient().report(value.text,value.capture_ids)
            except APIError: raise HTTPException(422,'Local demo supports the two prepared citation examples only') from None
            result['report_id']=uid('report')
        else: raise HTTPException(503,'Citation verifier is not configured')
        result['fixture']=settings.demo
        conn.execute(insert(db.reports).values(id=result['report_id'],org_id=p['org_id'],payload={**result,'text':value.text,'capture_ids':value.capture_ids},created_at=now()))
        event(conn,p,'report.created',result['report_id']);return result
    @app.get('/reports/{id}')
    def get_report(id:str,p=Depends(human),conn=Depends(connection)): return owned(conn,db.reports,id,p)['payload']
    @app.get('/ledger')
    def ledger(p=Depends(human),conn=Depends(connection)):
        # A single ordered snapshot query avoids a root derived from multiple inconsistent pages.
        rows=conn.execute(select(db.captures.c.payload).where(db.captures.c.org_id==p['org_id']).order_by(db.captures.c.sequence).limit(10001)).scalars().all()
        if len(rows)>10000: raise HTTPException(413,'Synchronous ledger limit reached; use a background snapshot/export worker')
        return {'records':rows,'merkle_root':merkle_root([r['record_hash'] for r in rows]),'anchor_tx':None,'chain_ok':None,
                'chain_msg':'Whole-chain audit has not been run. Merkle root describes this ordered snapshot only.','fixture':settings.demo}
    @app.post('/ledger/anchor')
    def anchor(p=Depends(admin)): raise HTTPException(503,'Connect the owner-managed durable Sepolia submission workflow; no transaction was sent')
    @app.get('/pubkey')
    def pubkey(device_id:str,p=Depends(human),conn=Depends(connection)):
        row=owned(conn,db.devices,device_id,p)
        if not row['public_key']: raise HTTPException(404,'No public key enrolled for this device')
        return Response(row['public_key'],media_type='text/plain')
    return app
