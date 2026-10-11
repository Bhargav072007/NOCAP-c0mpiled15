"""Open full-text retrieval with abstract fallback and retraction evidence."""
import io
import os
import re
from functools import lru_cache
from urllib.parse import quote
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from .http import get_json, get_bytes, DependencyError

class SourceError(ValueError): pass

def xml_article(raw):
    root=ET.fromstring(raw)
    parts=[]
    for tag in ('article-title','abstract','body'):
        for element in root.iter(tag):
            parts.append(' '.join(' '.join(element.itertext()).split()))
    return '\n\n'.join(parts)

def document_text(raw, content_type=''):
    if raw.startswith(b'%PDF'):
        from pypdf import PdfReader
        return '\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(raw)).pages)
    if 'xml' in content_type or b'<article' in raw[:3000]:
        return xml_article(raw)
    soup=BeautifulSoup(raw,'html.parser')
    for el in soup(['script','style','nav','header','footer']): el.decompose()
    main=soup.find('article') or soup.find('main') or soup
    return main.get_text(' ',strip=True)

def openalex(doi):
    headers={'Authorization':'Bearer '+os.environ['OPENALEX_API_KEY']} if os.getenv('OPENALEX_API_KEY') else {}
    return get_json('https://api.openalex.org/works/'+quote('https://doi.org/'+doi,safe=''),headers=headers)

def semantic(doi):
    headers={'x-api-key':os.environ['SEMANTIC_SCHOLAR_API_KEY']} if os.getenv('SEMANTIC_SCHOLAR_API_KEY') else {}
    return get_json('https://api.semanticscholar.org/graph/v1/paper/DOI:'+quote(doi,safe=''),
                    {'fields':'title,abstract,url,openAccessPdf,authors,year,externalIds'},headers)

@lru_cache(maxsize=512)
def source_for(doi):
    errors=[]; retractions=[]; oa=None; ss=None
    try:
        oa=openalex(doi)
        if oa is not None and type(oa.get('is_retracted')) is bool:
            retractions.append({'provider':'OpenAlex','retracted':oa['is_retracted'],'url':oa.get('id')})
    except DependencyError: errors.append('OpenAlex unavailable or needs API key')
    try: ss=semantic(doi)
    except DependencyError: errors.append('Semantic Scholar unavailable')
    retract='retracted' if any(r['retracted'] for r in retractions) else 'not_marked' if retractions else 'unknown'
    base={'doi':doi,'retraction':retract,'retraction_evidence':retractions,'errors':errors,'trust_level':'external'}
    # Europe PMC provides licensed fullTextXML only when available.
    try:
        search=get_json('https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                        {'query':'DOI:"'+doi+'"','format':'json','resultType':'core','pageSize':1})
        found=(search or {}).get('resultList',{}).get('result',[])
        pmcid=found[0].get('pmcid') if found else None
        if pmcid and re.fullmatch(r'PMC\d+',pmcid):
            url='https://www.ebi.ac.uk/europepmc/webservices/rest/'+pmcid+'/fullTextXML'
            raw,kind,final=get_bytes(url)
            root=ET.fromstring(raw)
            identities=[e.text.strip().lower() for e in root.iter('article-id') if e.attrib.get('pub-id-type')=='doi' and e.text]
            if doi.lower() not in identities:
                raise SourceError('Full-text DOI does not match requested publication')
            text=xml_article(raw)
            if text.strip():
                return base | {'text':text,'provider':'Europe PMC','url':final,'scope':'full_text',
                               'license':found[0].get('license','provider-permitted retrieval')}
    except (DependencyError,ET.ParseError,ValueError): errors.append('Europe PMC full text unavailable')
    # Only OA links advertised by scholarly metadata; never arbitrary manuscript URLs.
    urls=[]
    if ss and ss.get('openAccessPdf',{}): urls.append(ss['openAccessPdf'].get('url'))
    if oa:
        for location in oa.get('locations',[]):
            if location.get('is_oa') and location.get('pdf_url'): urls.append(location['pdf_url'])
    for url in dict.fromkeys(u for u in urls if u):
        try:
            raw,kind,final=get_bytes(url)
            if not raw.startswith(b'%PDF'):
                raise SourceError('Advertised OA PDF returned a non-PDF document')
            text=document_text(raw,kind)
            title=(ss or {}).get('title') or (oa or {}).get('title') or ''
            nt=lambda value:' '.join(re.findall(r'\w+',value.casefold()))
            if not title or nt(title) not in nt(text[:8000]):
                raise SourceError('Full-text title could not be matched to the publication')
            if len(text)>1000:
                return base | {'text':text,'provider':'Open-access source','url':final,'scope':'full_text'}
        except Exception:
            errors.append('Advertised OA source unavailable or unparsable')
    abstract=(ss or {}).get('abstract') or (found[0].get('abstractText','') if 'found' in locals() and found else '')
    if not abstract and oa:
        index=oa.get('abstract_inverted_index') or {}
        pos={p:w for w,ps in index.items() for p in ps}
        abstract=' '.join(pos[p] for p in sorted(pos))
    if abstract:
        abstract=BeautifulSoup(abstract,'html.parser').get_text(' ',strip=True)
    return base | {'text':abstract,'provider':'Scholarly abstract','url':'https://doi.org/'+doi,'scope':'abstract' if abstract else 'missing'}

def select_passages(claim,text, *, limit=18000):
    """Keep offsets for auditable, claim-relevant excerpts; do not imply exhaustive reading."""
    if len(text)<=limit: return text,[{'start':0,'end':len(text)}],False
    tokens=set(re.findall(r'\w{3,}',claim.casefold()))
    windows=[(i,text[i:i+2000]) for i in range(0,len(text),1700)]
    ranked=sorted(windows,key=lambda x:len(tokens & set(re.findall(r'\w{3,}',x[1].casefold()))),reverse=True)[:8]
    selected=sorted(ranked)
    return '\n\n'.join(s for _,s in selected),[{'start':i,'end':i+len(s)} for i,s in selected],True
