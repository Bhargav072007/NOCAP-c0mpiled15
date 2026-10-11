"""US case citations: Eyecite parsing, exact CourtListener resolution and opinion evidence."""
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .http import request_json, get_json, DependencyError
from .citations import normalize

BASE='https://www.courtlistener.com/api/rest/v4'

def legal_citations(text):
    from eyecite import get_citations
    from eyecite.models import FullCaseCitation
    return [c for c in get_citations(text) if isinstance(c,FullCaseCitation)]

def is_legal(ref):
    return bool(legal_citations(ref))

def auth():
    token=os.getenv('COURTLISTENER_API_TOKEN')
    if not token: raise DependencyError('Set COURTLISTENER_API_TOKEN for live US case-law lookup')
    return {'Authorization':'Token '+token}

@lru_cache(maxsize=512)
def lookup_case(ref):
    response=request_json(BASE+'/citation-lookup/',headers=auth(),data={'text':ref})
    if not isinstance(response,list): raise DependencyError('Invalid CourtListener lookup response')
    return response

def check_legal_reference(ref, metadata=None):
    base={'citation':ref,'matched_title':None,'doi':None,'confidence':0.0,'evidence':[],
          'retraction_check':'not_applicable','legal_validity_check':'not_checked'}
    try: matches=lookup_case(ref)
    except DependencyError as exc: return base | {'status':'NEEDS_REVIEW','reason':str(exc)}
    if not matches:
        return base | {'status':'NEEDS_REVIEW','reason':'No complete US case citation parsed; statutes, id., supra and non-US sources need another resolver'}
    # References with multiple cases are separate findings, never pick one silently.
    if len(matches)!=1:
        return base | {'status':'NEEDS_REVIEW','reason':'Reference contains multiple case citations; split into individual cases','evidence':matches}
    match=matches[0];code=match.get('status');clusters=match.get('clusters',[])
    if code in (400,404):
        return base | {'status':'NOT_FOUND','reason':'Case citation not resolved in CourtListener; database coverage is incomplete','confidence':.75,'evidence':matches}
    if code!=200 or len(clusters)!=1:
        return base | {'status':'NEEDS_REVIEW','reason':'Case citation ambiguous or lookup throttled','evidence':matches}
    cluster=clusters[0];name=cluster.get('case_name') or cluster.get('case_name_full') or ''
    mismatches=[];metadata=metadata or {}
    claimed_name=metadata.get('title','')
    if claimed_name and SequenceMatcher(None,normalize(claimed_name),normalize(name)).ratio()<.9:
        mismatches.append('case name differs')
    year=metadata.get('year')
    if year and cluster.get('date_filed','')[:4]!=str(year): mismatches.append('decision year differs or unavailable')
    # Use CourtListener's corrected citation but report typos rather than hiding them.
    normalized=match.get('normalized_citations',[])
    if match.get('citation') and normalized and normalize(match['citation']) not in {normalize(c) for c in normalized}:
        mismatches.append('reporter abbreviation differs from canonical citation')
    return base | {'status':'MISMATCH' if mismatches else 'VERIFIED','reason':'; '.join(mismatches) or 'Reporter citation resolves to a unique case',
        'matched_title':name,'confidence':.95,'evidence':matches,'cluster':cluster,
        'source_url':'https://www.courtlistener.com'+cluster.get('absolute_url','')}

@lru_cache(maxsize=512)
def case_source(cluster_id, opinion_urls):
    # API URLs are derived only from provider metadata and restricted to /opinions/{id}/.
    opinions=[]
    for url in opinion_urls:
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='www.courtlistener.com' or parsed.port not in (None,443) or parsed.username or parsed.password or not re.fullmatch(r'/api/rest/v4/opinions/\d+/',parsed.path):
            continue
        opinion=get_json(url,headers=auth())
        if not opinion: continue
        raw=opinion.get('html_with_citations') or opinion.get('plain_text') or opinion.get('html') or opinion.get('html_lawbox') or opinion.get('html_columbia') or ''
        text=BeautifulSoup(raw,'html.parser').get_text(' ',strip=True) if '<' in raw else raw
        if text: opinions.append({'text':text,'opinion_id':opinion.get('id'),'type':opinion.get('type'),'url':url})
    majority=[x for x in opinions if x['type'] in ('010combined','020lead')]
    chosen=majority or opinions
    return {'text':'\n\n'.join(x['text'] for x in chosen),'scope':'full_text' if chosen else 'missing',
        'provider':'CourtListener','url':f'https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/',
        'opinions':chosen,'majority_identified':bool(majority),'legal_validity_check':'not_checked',
        'trust_level':'external'}

def source_for_case(result):
    cluster=result.get('cluster',{})
    if not cluster.get('id'): return {'text':'','scope':'missing','provider':'CourtListener'}
    urls=tuple(cluster.get('sub_opinions') or [])
    try: return case_source(cluster['id'],urls)
    except DependencyError as exc: return {'text':'','scope':'missing','provider':'CourtListener','errors':[str(exc)]}

def extract_legal_items(text):
    """Deterministic citation coverage, even when the model misses a case."""
    items=[]
    for citation in legal_citations(text):
        start,end=citation.span()
        # Periods inside reporter names are not sentence boundaries: use newlines and punctuation with following capitals.
        left=text.rfind('\n',0,start)+1
        right=text.find('\n',end)
        if right<0: right=len(text)
        sentence=text[left:right].strip()
        metadata=citation.metadata
        name=''
        if getattr(metadata,'plaintiff',None) and getattr(metadata,'defendant',None):
            name=f'{metadata.plaintiff} v. {metadata.defendant}'
        items.append({'claim':sentence,'citation':text[start:end],'title':name,'authors':[],
            'year':int(metadata.year) if getattr(metadata,'year',None) and str(metadata.year).isdigit() else None,'unresolved':False})
    return items
