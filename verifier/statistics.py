"""Explicitly linked numeric claims, finite observations, sample SD and two-sided tests."""
import csv
import json
import math
from pathlib import Path
import numpy as np
from scipy import stats

class DataError(ValueError): pass

def rows_for(path):
    path=Path(path)
    if path.stat().st_size>20_000_000: raise DataError('Dataset exceeds 20 MB limit')
    if path.suffix.lower()=='.json':
        raw=json.loads(path.read_text())
        rows=raw if isinstance(raw,list) else raw.get('readings') if isinstance(raw,dict) and 'readings' in raw else [raw]
        if not isinstance(rows,list) or any(not isinstance(x,dict) for x in rows): raise DataError('Expected JSON observation objects')
        return rows
    with path.open(newline='',encoding='utf-8-sig') as stream: return list(csv.DictReader(stream))

def numeric(rows,column):
    values=[];missing=0
    if not column or any(column not in row for row in rows): raise DataError('Numeric column missing')
    for row in rows:
        value=row[column]
        if value is None or str(value).strip()=='': missing+=1;continue
        try: number=float(value)
        except (ValueError,TypeError) as exc: raise DataError('Non-numeric observation') from exc
        if not math.isfinite(number): raise DataError('Non-finite observation')
        values.append(number)
    if not values: raise DataError('No usable observations')
    return np.array(values,dtype=float),missing

def recompute(path,claim):
    rows=rows_for(path);column=claim.get('column','');metric=claim.get('metric')
    group_column=claim.get('group_column','');test=claim.get('test','none')
    if group_column:
        if any(group_column not in r for r in rows): raise DataError('Grouping column missing')
        group_a=[r for r in rows if str(r[group_column])==str(claim.get('group_a'))]
        group_b=[r for r in rows if str(r[group_column])==str(claim.get('group_b'))]
    else: group_a=rows;group_b=[]
    a,missing=numeric(group_a,column)
    result={'n':int(len(a)),'mean':float(np.mean(a)),'missing':missing,
            'std':float(np.std(a,ddof=1)) if len(a)>1 else None,'test':test}
    if metric=='value':
        if len(a)!=1: raise DataError('Exact reading requires a single selected observation')
        result['value']=float(a[0])
    if metric=='p_value' or claim.get('significant'):
        if test=='welch':
            if not group_column or not group_b: raise DataError('Welch test requires two explicit groups')
            b,missing_b=numeric(group_b,column)
            if len(a)<2 or len(b)<2: raise DataError('Each group needs at least two observations')
            if np.var(a)==0 and np.var(b)==0: raise DataError('Both groups constant; t-test inference undefined')
            p=float(stats.ttest_ind(a,b,equal_var=False).pvalue)
            result.update(n_b=int(len(b)),mean_b=float(np.mean(b)),missing_b=missing_b)
        elif test=='paired':
            paired=claim.get('paired_column','')
            # Complete-case pairing preserves row alignment, never drop independently.
            complete=[r for r in group_a if r.get(column) not in ('',None) and r.get(paired) not in ('',None)]
            a,_=numeric(complete,column);b,_=numeric(complete,paired)
            if len(a)<2 or np.std(a-b)==0: raise DataError('Paired differences need nonzero variance and at least two pairs')
            p=float(stats.ttest_rel(a,b).pvalue)
            result.update(paired_n=int(len(a)),paired_missing=len(group_a)-len(complete))
        else: raise DataError('p-value/significance needs an explicitly specified paired or Welch test')
        if not math.isfinite(p): raise DataError('Statistical test returned undefined p-value')
        result['p_value']=p
    result['value_for_claim']=result.get(metric)
    if metric not in ('none',None) and result['value_for_claim'] is None: raise DataError('Requested statistic cannot be computed')
    return result

def compare_reported(reported,actual, *, metric,decimals=None,atol=1e-8,rtol=.01):
    if type(reported) not in (int,float) or not math.isfinite(reported): raise DataError('Reported value must be finite')
    if metric=='n': return reported==actual
    tolerance=.5*10**(-decimals) if decimals is not None else atol
    return abs(reported-actual)<=max(tolerance,rtol*abs(actual))
