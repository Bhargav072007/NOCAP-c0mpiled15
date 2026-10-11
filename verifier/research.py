"""Bounded discovery of independent literature using explicit reviewer search queries."""
import hashlib
from .http import get_json, DependencyError
from .sources import source_for

def independent_sources(queries):
    if not isinstance(queries,list) or len(queries)>3 or any(not isinstance(q,str) or not 1<=len(q.strip())<=300 for q in queries):
        raise ValueError('research_queries must contain at most three nonempty strings of at most 300 characters')
    sources=[];audit=[];seen=set()
    for query in queries:
        record={'query':query,'provider':'Crossref','candidates':[],'errors':[]}
        try:
            payload=get_json('https://api.crossref.org/works',{'query':query,'rows':2})
            items=(payload or {}).get('message',{}).get('items',[])
            if not isinstance(items,list):raise DependencyError('Invalid literature search response')
            for hit in items:
                doi=hit.get('DOI');candidate={'doi':doi,'title':(hit.get('title') or [''])[0],
                    'ranking_score':hit.get('score'),'url':hit.get('URL')}
                record['candidates'].append(candidate)
                if not doi or doi in seen:continue
                seen.add(doi);source=source_for(doi)
                candidate.update(scope=source.get('scope'),retraction=source.get('retraction'),errors=source.get('errors',[]))
                if source.get('text'):
                    sources.append({**source,'id':'independent_'+hashlib.sha256(doi.encode()).hexdigest()[:16],
                        'title':candidate['title'],'source_url':source.get('url') or 'https://doi.org/'+doi,
                        'identity_reviewed':source.get('trust_level')=='external',
                        'discovery_query':query,'relevance':'not independently established; model and reviewer must evaluate'})
        except DependencyError as exc:record['errors'].append(str(exc))
        audit.append(record)
    return sources,audit
