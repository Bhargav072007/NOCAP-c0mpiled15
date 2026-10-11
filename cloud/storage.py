"""Originals stay private. The API controls reads; filenames never become keys."""
from pathlib import Path
from botocore.config import Config

class LocalStorage:
    def __init__(self,root): self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def path(self,key):
        p=(self.root/key).resolve()
        if self.root not in p.parents: raise ValueError('Invalid object key')
        return p
    def put(self,key,data):
        p=self.path(key);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(data)
    def get(self,key): return self.path(key).read_bytes()
    def delete(self,key): self.path(key).unlink(missing_ok=True)

class S3Storage:
    def __init__(self,bucket,region,client=None):
        import boto3
        self.bucket=bucket
        self.client=client or boto3.client('s3',region_name=region,config=Config(connect_timeout=3,read_timeout=20,retries={'max_attempts':2}))
    def put(self,key,data):
        self.client.put_object(Bucket=self.bucket,Key=key,Body=data,ServerSideEncryption='AES256',ContentType='application/octet-stream')
    def get(self,key):
        response=self.client.get_object(Bucket=self.bucket,Key=key)
        try: return response['Body'].read(50*1024*1024+1)
        finally: response['Body'].close()
    def delete(self,key): self.client.delete_object(Bucket=self.bucket,Key=key)

def storage_for(settings):
    return S3Storage(settings.bucket,settings.region) if settings.storage=='s3' else LocalStorage(settings.media_dir)
