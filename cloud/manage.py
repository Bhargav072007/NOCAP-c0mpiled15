"""Operator-only identity provisioning. Writes credentials to a 0600 file, never stdout.
Run on the API host after approved migrations. No email is sent.
"""
import argparse,os,secrets
from datetime import datetime,timezone,timedelta
from sqlalchemy import insert,select,update
from cloud import db
from cloud.config import Settings
from cloud.api import digest,uid

def issue(conn,org_id,member_id,output,hours):
    if not conn.execute(select(db.members.c.id).where(db.members.c.id==member_id,db.members.c.org_id==org_id,db.members.c.active==True)).first(): raise ValueError('Active membership not found')
    token=secrets.token_urlsafe(32)
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        conn.execute(insert(db.tokens).values(digest=digest(token),org_id=org_id,member_id=member_id,revoked=False,expires_at=(datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()))
        with os.fdopen(fd,'w') as f: f.write(token+'\n')
    except Exception:
        os.unlink(output);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    org=sub.add_parser('create-org');org.add_argument('--name',required=True);org.add_argument('--admin-name',required=True);org.add_argument('--admin-email',required=True);org.add_argument('--output',required=True)
    token=sub.add_parser('issue-token');token.add_argument('--org',required=True);token.add_argument('--member',required=True);token.add_argument('--output',required=True);token.add_argument('--hours',type=int,default=24,choices=range(1,169))
    revoke=sub.add_parser('revoke-tokens');revoke.add_argument('--org',required=True);revoke.add_argument('--member',required=True)
    args=p.parse_args();engine=db.engine_for(Settings.env())
    with engine.begin() as conn:
        if args.action=='create-org':
            org_id=uid('org');member_id=uid('mem')
            conn.execute(insert(db.orgs).values(id=org_id,name=args.name))
            conn.execute(insert(db.members).values(id=member_id,org_id=org_id,name=args.admin_name,email=args.admin_email.lower(),role='admin',active=True))
            issue(conn,org_id,member_id,args.output,24);print('Organization:',org_id,'Admin member:',member_id)
        elif args.action=='issue-token': issue(conn,args.org,args.member,args.output,args.hours)
        else: conn.execute(update(db.tokens).where(db.tokens.c.org_id==args.org,db.tokens.c.member_id==args.member).values(revoked=True))
    print('Identity operation completed. Credentials, when issued, are in the specified private file.')
