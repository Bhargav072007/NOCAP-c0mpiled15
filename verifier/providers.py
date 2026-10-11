"""Scholarly fallback records normalized to the Crossref matching shape."""
import os
from urllib.parse import quote
from .http import get_json, DependencyError
from .sources import openalex, semantic

def oa_record(p):
    authors=[{'family':a.get('author',{}).get('display_name','').split()[-1]} for a in p.get('authorships',[]) if a.get('author',{}).get('display_name')]
    return {'title':[p.get('title','')],'DOI':(p.get('doi') or '').replace('https://doi.org/',''),
        'author':authors,'published':{'date-parts':[[p.get('publication_year')]]} if p.get('publication_year') else {},
        'relation':{'is-retracted-by':[{'provider':'OpenAlex'}]} if p.get('is_retracted') else {},'provider':'OpenAlex','provider_record':p}

def ss_record(p):
    return {'title':[p.get('title','')],'DOI':p.get('externalIds',{}).get('DOI'),
        'author':[{'family':a.get('name','').split()[-1]} for a in p.get('authors',[]) if a.get('name')],
        'published':{'date-parts':[[p['year']]]} if p.get('year') else {},'provider':'Semantic Scholar','provider_record':p}

def fallback_candidates(ref,doi):
    hits=[];errors=[]
    try:
        if doi: papers=[openalex(doi)]
        else:
            headers={'Authorization':'Bearer '+os.environ['OPENALEX_API_KEY']} if os.getenv('OPENALEX_API_KEY') else {}
            papers=(get_json('https://api.openalex.org/works',{'search':ref,'per-page':5},headers) or {}).get('results',[])
        hits.extend(oa_record(p) for p in papers if p)
    except DependencyError: errors.append('OpenAlex unavailable')
    try:
        if doi: papers=[semantic(doi)]
        else:
            headers={'x-api-key':os.environ['SEMANTIC_SCHOLAR_API_KEY']} if os.getenv('SEMANTIC_SCHOLAR_API_KEY') else {}
            papers=(get_json('https://api.semanticscholar.org/graph/v1/paper/search',
                {'query':ref,'limit':5,'fields':'title,authors,year,externalIds'},headers) or {}).get('data',[])
        hits.extend(ss_record(p) for p in papers if p)
    except DependencyError: errors.append('Semantic Scholar unavailable')
    return hits,errors
