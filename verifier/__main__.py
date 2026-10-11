import argparse,json
from pathlib import Path
from . import analyse_document,InputError

def load_context(path):
    data=json.loads(path.read_text());base=path.parent.resolve()
    for kind in ('captures','datasets','figures','sources'):
        for entry in data.get(kind,[]):
            if entry.get('path'):
                p=Path(entry['path']);entry['path']=str(p if p.is_absolute() else (base/p).resolve())
                if kind=='sources':
                    from .parser import parse_document
                    if p.suffix.lower() in ('.pdf','.docx','.tex'):
                        entry['text']=parse_document(entry['path'])['text']
                    else:
                        if Path(entry['path']).stat().st_size>50_000_000:raise ValueError('Source exceeds 50 MB limit')
                        entry['text']=Path(entry['path']).read_text()
    for device,key in list(data.get('public_keys',{}).items()):
        if not key.startswith('-----BEGIN'):
            p=Path(key);data['public_keys'][device]=(p if p.is_absolute() else base/p).read_text()
    return data

def main():
    parser=argparse.ArgumentParser(description='NoCap OpenAI/evidence assessment with local Qiskit review search')
    parser.add_argument('paper',type=Path);parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--assets',type=Path)
    parser.add_argument('--no-quantum',action='store_true');parser.add_argument('--shots',type=int,default=2048);parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--mode',choices=('hybrid','offline'),default='hybrid')
    parser.add_argument('--provider',choices=('openai','luminal'))
    parser.add_argument('--domain',choices=('mixed','academic','legal'),default='mixed')
    parser.add_argument('--skip-live-citations',action='store_true')
    parser.add_argument('--skip-data-extraction',action='store_true')
    parser.add_argument('--skip-science',action='store_true')
    args=parser.parse_args()
    try:
        if args.provider:
            import os
            os.environ['NOCAP_PROVIDER']=args.provider
        result=analyse_document(args.paper,context=load_context(args.context),asset_dir=args.assets,quantum=not args.no_quantum,shots=args.shots,seed=args.seed,mode=args.mode,domain=args.domain,run_citations=not args.skip_live_citations,extract_claims=not args.skip_data_extraction,scientific=not args.skip_science)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(2,str(exc)+'\n')
if __name__=='__main__':main()
