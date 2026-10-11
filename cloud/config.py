from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Settings:
    database_url: str = 'sqlite:///.runtime/nocap.db'
    storage: str = 'local'
    media_dir: str = '.runtime/media'
    bucket: str = ''
    region: str = 'us-east-2'
    demo: bool = True
    signing_plugin: str = ''
    verifier_plugin: str = ''
    verifier_mode: str = 'offline'
    verifier_quantum: bool = False
    max_upload: int = 50 * 1024 * 1024

    @classmethod
    def env(cls):
        return cls(database_url=os.getenv('DATABASE_URL','sqlite:///.runtime/nocap.db'),
                   storage=os.getenv('NOCAP_STORAGE','local'),media_dir=os.getenv('NOCAP_MEDIA_DIR','.runtime/media'),
                   bucket=os.getenv('S3_BUCKET',os.getenv('S3_BUCKET_NAME','')),region=os.getenv('AWS_REGION','us-east-2'),
                   demo=os.getenv('NOCAP_BACKEND_MODE','demo')=='demo',
                   signing_plugin=os.getenv('NOCAP_SIGNING_PLUGIN',''),verifier_plugin=os.getenv('NOCAP_VERIFIER_PLUGIN',''),
                   verifier_mode=os.getenv('NOCAP_VERIFIER_MODE','offline'),
                   verifier_quantum=os.getenv('NOCAP_VERIFIER_QUANTUM','0')=='1')

    def validate(self):
        if self.verifier_mode not in {'offline','hybrid'}: raise ValueError('Verifier mode must be offline or hybrid')
        from sqlalchemy.engine import make_url
        url=make_url(self.database_url)
        if self.storage not in {'local','s3'}: raise ValueError('Storage must be local or s3')
        if self.storage=='s3' and not self.bucket: raise ValueError('S3_BUCKET is required')
        if url.drivername.startswith('postgresql'):
            if url.query.get('sslmode')!='verify-full' or not url.query.get('sslrootcert'):
                raise ValueError('PostgreSQL requires sslmode=verify-full and sslrootcert')
        if not self.demo and url.drivername.startswith('sqlite'):
            raise ValueError('Production configuration requires PostgreSQL; SQLite is local-demo only')
