"""Frozen initial integration schema; review before applying to RDS."""
from alembic import op
from sqlalchemy import (MetaData,Table,Column,String,Integer,Text,JSON,Boolean,Index,UniqueConstraint,create_engine,event)
metadata=MetaData()
orgs=Table('organizations',metadata,Column('id',String(64),primary_key=True),Column('name',String(120),nullable=False))
members=Table('members',metadata,Column('id',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('name',String(120),nullable=False),Column('email',String(254),nullable=False),Column('role',String(24),nullable=False),Column('active',Boolean,nullable=False,default=True),UniqueConstraint('org_id','email'))
tokens=Table('access_tokens',metadata,Column('digest',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('member_id',String(64)),Column('device_id',String(64)),Column('expires_at',String(40)),Column('revoked',Boolean,nullable=False,default=False))
devices=Table('devices',metadata,Column('id',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('name',String(120),nullable=False),Column('location',String(240),nullable=False),Column('public_key',Text,nullable=False,default=''),Column('enabled',Boolean,nullable=False,default=True),Column('last_seen',String(40)),Column('firmware',String(80)),Column('fixture',Boolean,nullable=False,default=False),Column('last_hash',String(64),nullable=False,default='0'*64))
captures=Table('captures',metadata,Column('sequence',Integer,primary_key=True,autoincrement=True),Column('org_id',String(64),nullable=False),Column('id',String(64),nullable=False),Column('device_id',String(64),nullable=False),Column('file_sha256',String(64),nullable=False),Column('record_hash',String(64),nullable=False),Column('payload',JSON,nullable=False),Column('object_key',String(300),nullable=False),Column('created_at',String(40),nullable=False),UniqueConstraint('org_id','id'),Index('ix_captures_org_sequence','org_id','sequence'),Index('ix_captures_org_digest','org_id','file_sha256'))
reports=Table('reports',metadata,Column('id',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('payload',JSON,nullable=False),Column('created_at',String(40),nullable=False))
work=Table('work_items',metadata,Column('id',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('title',String(200),nullable=False),Column('section',String(120),nullable=False),Column('owner_id',String(64),nullable=False),Column('status',String(30),nullable=False),Column('priority',String(16),nullable=False),Column('capture_id',String(64)),Column('version',Integer,nullable=False,default=1),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False))
comments=Table('comments',metadata,Column('id',String(64),primary_key=True),Column('org_id',String(64),nullable=False,index=True),Column('work_id',String(64),nullable=False,index=True),Column('author_id',String(64),nullable=False),Column('body',Text,nullable=False),Column('created_at',String(40),nullable=False))
audit=Table('audit_events',metadata,Column('sequence',Integer,primary_key=True,autoincrement=True),Column('org_id',String(64),nullable=False,index=True),Column('actor',String(64),nullable=False),Column('action',String(100),nullable=False),Column('target',String(64),nullable=False),Column('created_at',String(40),nullable=False))

revision="0001"
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): metadata.create_all(op.get_bind())
def downgrade(): raise RuntimeError("Destructive downgrade requires manual backup and review")
