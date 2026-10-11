"""Probe HTTPS health; optionally submit one explicit device-token upload.
Does not print credentials or the server response body. No automatic retry.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from device.upload import upload,device_token

if __name__=='__main__':
    from dotenv import load_dotenv
    load_dotenv()
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--file',help='Send this file once. Without this option, only health is checked.')
    parser.add_argument('--record',help='Signed JSON record for an enrolled source')
    parser.add_argument('--metadata',help='JSON lab annotations')
    args=parser.parse_args()
    if not args.url.startswith('https://'): parser.error('Use the deployed HTTPS URL')
    response=requests.get(args.url.rstrip('/')+'/health',timeout=(5,20),allow_redirects=False)
    print(json.dumps({'health_http_status':response.status_code}))
    response.raise_for_status()
    if args.file:
        value=upload(args.url,device_token(),args.record,args.file,
                     metadata=json.loads(Path(args.metadata).read_text()) if args.metadata else None)
        safe={key:value[key] for key in ('id','capture_id','sha256','status','file_sha256','record_hash','metadata_signed','media') if key in value}
        print(json.dumps({'upload_accepted':True,'receipt':safe}))
