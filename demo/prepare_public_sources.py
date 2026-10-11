"""Fetch the two public paper fixtures; originals are not bundled in the archive."""
import argparse,hashlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from verifier.http import get_bytes
from pypdf import PdfReader

FIXTURES=[
 {'id':'rr-original','cache_file':'rr_nber.pdf','url':'https://www.nber.org/system/files/working_papers/w15639/w15639.pdf','sha256':'4e522bb976cf2a2ffead5829c1f316d46e283e4125890342b1b15a19523cc10f','leading_newline':False},
 {'id':'rr-replication','cache_file':'hap.pdf','url':'https://peri.umass.edu/images/WP322.pdf','sha256':'b481030e538a1222fb1116bd2cc0646d031b8e36a0bf3b7057f1378800e0f0e5','leading_newline':True},
]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--cache-dir',type=Path)
 args=parser.parse_args();records=[]
 for fixture in FIXTURES:
  cached=args.cache_dir/fixture['cache_file'] if args.cache_dir else None
  raw=cached.read_bytes() if cached and cached.is_file() else get_bytes(fixture['url'])[0]
  digest=hashlib.sha256(raw).hexdigest()
  if digest!=fixture['sha256']:raise ValueError('Publication version changed; review fixture identity before using '+fixture['id'])
  prefix='\n' if fixture['leading_newline'] else ''
  text='\n'.join(prefix+'[PDF PAGE '+str(i+1)+']\n'+(page.extract_text() or '') for i,page in enumerate(PdfReader(io.BytesIO(raw)).pages))
  (ROOT/'demo'/(fixture['id']+'.txt')).write_text(text)
  records.append({'id':fixture['id'],'source_url':fixture['url'],'original_pdf_sha256':digest,'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
 (ROOT/'demo/source_fixture_manifest.json').write_text(json.dumps(records,indent=2))
 print('Prepared identity-checked public source fixtures.')
if __name__=='__main__':main()
