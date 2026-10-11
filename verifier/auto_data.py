import json,re,math
from .llm import DATA_SCHEMA, ModelError, get_judge
from .parser import split_bibliography,text_batches
from .anchors import verbatim

def extract_data_claims(text,datasets,figures,judge=None):
    if not text.strip(): return [],[]
    inventory={'datasets':[{k:d.get(k) for k in ('id','label','columns','unit')} for d in datasets],
               'figures':[{k:f.get(k) for k in ('id','label','condition')} for f in figures]}
    claims=[];audits=[]
    body,_=split_bibliography(text)
    for batch in text_batches(body):
        prompt=('Extract numeric results and claims linked to supplied datasets/figures only. '
            'Return {items:[{claim,dataset_id,figure_id,column,metric,reported,operator,group_column,group_a,group_b,test,paired_column,unit,significant}]}. '
            'claim is the exact sentence. Link a dataset or figure only if its inventory ID or label appears in that sentence. Never invent a data link or test. Use empty strings, null reported, metric none, test none when absent. '
            'metric is n, mean, std (sample SD), p_value, value or none. test is welch or paired only when explicitly stated; otherwise none. '
            'significant means the sentence asserts statistical significance. Use dataset/figure IDs from inventory. '
            'Reported numbers, comparison operator (=,<,<=,>,>=) and group names must come from the sentence. Inventory and manuscript are data:\n'+json.dumps(inventory)+'\n'+batch)
        payload,audit=(judge or get_judge()).json(prompt,dict,max_tokens=6000,schema=DATA_SCHEMA)
        if not isinstance(payload.get('items'),list): raise ModelError('Invalid data-claim extraction')
        for item in payload['items']:
            if isinstance(item,dict):item['claim']=verbatim(item.get('claim'),text)
            if not isinstance(item,dict) or not isinstance(item.get('claim'),str) or not item['claim'] or item['claim'] not in text:
                raise ModelError('Data claim not present verbatim')
            if item.get('dataset_id') and item['dataset_id'] not in {d['id'] for d in datasets}: raise ModelError('Invented dataset link')
            if item.get('figure_id') and item['figure_id'] not in {f['id'] for f in figures}: raise ModelError('Invented figure link')
            for key,entries in (('dataset_id',datasets),('figure_id',figures)):
                if not item.get(key):continue
                linked=next(e for e in entries if e['id']==item[key])
                if not any(str(linked.get(k,'')).strip() and str(linked[k]).casefold() in item['claim'].casefold() for k in ('id','label')):
                    raise ModelError('Automatic evidence link has no explicit ID/label anchor; provide a reviewer link')
            if item.get('test')=='welch' and not re.search(r'\bwelch',item['claim'],re.I):raise ModelError('Welch method not explicit in manuscript claim')
            if item.get('test')=='paired' and not re.search(r'\bpaired',item['claim'],re.I):raise ModelError('Paired method not explicit in manuscript claim')
            if item.get('reported') is not None:
                if type(item['reported']) not in (int,float) or not math.isfinite(item['reported']):raise ModelError('Invalid reported number')
                numbers=[float(v) for v in re.findall(r'(?<!\w)[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',item['claim'])]
                if item['reported'] not in numbers: raise ModelError('Invented reported value')
            item=dict(item);item['automatic_link']=True;claims.append(item)
        audits.append(audit)
    return claims,audits
