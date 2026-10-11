from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,field_validator
from datetime import datetime

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class MemberIn(Strict):
    name: str=Field(min_length=1,max_length=120)
    email: str=Field(min_length=3,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    role: Literal['admin','reviewer','collaborator']='collaborator'
class DeviceIn(Strict):
    name: str=Field(min_length=1,max_length=120)
    location: str=Field(default='',max_length=240)
    public_key: str=Field(default='',max_length=4096)
class Heartbeat(Strict):
    firmware: str=Field(min_length=1,max_length=80)
class WorkIn(Strict):
    title: str=Field(min_length=1,max_length=200)
    section: str=Field(min_length=1,max_length=120)
    owner_id: str=Field(min_length=1,max_length=64)
    priority: Literal['Normal','High','Urgent']='Normal'
    capture_id: str|None=Field(default=None,max_length=64)
class WorkUpdate(Strict):
    version: int=Field(ge=1)
    status: Literal['To review','In progress','Changes requested','Approved']
    owner_id: str=Field(min_length=1,max_length=64)
class CommentIn(Strict):
    body: str=Field(min_length=1,max_length=5000)
class ReportIn(Strict):
    text: str=Field(min_length=1,max_length=50000)
    capture_ids: list[str]=Field(default_factory=list,max_length=100)
    mode: Literal['configured','offline','hybrid','demo']='configured'
class CaptureMetadata(Strict):
    label: str=Field(default='',max_length=160)
    experiment_id: str=Field(default='',max_length=120)
    sample_id: str=Field(default='',max_length=120)
    notes: str=Field(default='',max_length=2000)

class CaptureIn(BaseModel):
    # Do not normalize signed field bytes: retain original strings exactly.
    model_config=ConfigDict(extra='forbid')
    id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    type: Literal['photo','video','audio','reading']
    file_name: str=Field(min_length=1,max_length=255,pattern=r'^[^/\\\x00-\x1f]+$')
    file_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    captured_at: str=Field(max_length=40)
    device_id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    location: str=Field(max_length=240)
    prev_hash: str=Field(pattern=r'^[0-9a-f]{64}$')
    record_hash: str=Field(pattern=r'^[0-9a-f]{64}$')
    signature: str=Field(pattern=r'^(?:[0-9a-fA-F]{128})?$',max_length=128)
    @field_validator('captured_at')
    @classmethod
    def utc(cls,value):
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.utcoffset() is None or dt.utcoffset().total_seconds()!=0: raise ValueError('UTC timestamp required')
        return value
