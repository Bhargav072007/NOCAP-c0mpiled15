import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from verifier import analyse
from verifier.llm import ModelError
from verifier.science import CATEGORIES, validate_assessment, assess_science, dataset_integrity

SCOPE={'org_id':'o','project_id':'p'}
CLAIM='The observational association proves causation.'
SOURCE={'id':'s','text':'This observational study cannot establish causation.',
        'identity_reviewed':True,'source_url':'https://example.org/study','scope':'full_text'}

def item(**kwargs):
    return dict(claim=CLAIM,category='causal_inference',verdict='CONCERN',
        reason='Causal wording exceeds observational design.',confidence=.9,
        suggested_fix='Describe association and limitations.',evidence=[{'source_id':'s','quote':SOURCE['text']}],**kwargs)

class Judge:
    model='test-double'
    def __init__(self,payload):self.payload=payload
    def json(self,*args,**kwargs):return self.payload,{'provider':'test-double'}

def payload(entry=None):
    return {'assessments':[entry or item()], 'coverage':[{'category':c,'state':'ASSESSED' if c=='causal_inference' else 'INSUFFICIENT_EVIDENCE','reason':'Review supplied evidence.'} for c in CATEGORIES]}

class HybridTests(unittest.TestCase):
    def test_grounded_concern(self):
        f=validate_assessment(item(),CLAIM,{'s':SOURCE})
        self.assertEqual(f['status'],'SCIENTIFIC_CONCERN');self.assertTrue(f['needs_human_review'])
    def test_invented_quote_rejected(self):
        x=item();x['evidence'][0]['quote']='fabricated'
        with self.assertRaises(ModelError):validate_assessment(x,CLAIM,{'s':SOURCE})
    def test_invented_source_rejected(self):
        with self.assertRaises(ModelError):validate_assessment(item(),CLAIM,{})
    def test_invented_claim_rejected(self):
        with self.assertRaises(ModelError):validate_assessment(item(),'Different manuscript',{'s':SOURCE})
    def test_unreviewed_source_abstains(self):
        self.assertEqual(validate_assessment(item(),CLAIM,{'s':{**SOURCE,'identity_reviewed':False}})['status'],'NEEDS_REVIEW')
    def test_no_evidence_abstains(self):
        x=item();x['evidence']=[];x['verdict']='NO_ISSUE_IDENTIFIED'
        self.assertEqual(validate_assessment(x,CLAIM,{})['status'],'NEEDS_REVIEW')
    def test_no_issue_is_not_truth_certification(self):
        x=item();x['verdict']='NO_ISSUE_IDENTIFIED'
        self.assertTrue(validate_assessment(x,CLAIM,{'s':SOURCE})['needs_human_review'])
    def test_low_confidence_abstains(self):
        x=item();x['confidence']=.4
        self.assertEqual(validate_assessment(x,CLAIM,{'s':SOURCE})['status'],'NEEDS_REVIEW')
    def test_inconsistent_positive_label_abstains(self):
        x=item();x.update(verdict='NO_ISSUE_IDENTIFIED',reason='The replication contradicts the original conclusion.')
        self.assertEqual(validate_assessment(x,CLAIM,{'s':SOURCE})['status'],'NEEDS_REVIEW')
    def test_invalid_confidence(self):
        for v in (True,float('nan'),-1,2):
            x=item();x['confidence']=v
            with self.assertRaises(ModelError):validate_assessment(x,CLAIM,{'s':SOURCE})
    def test_full_category_coverage(self):
        r=assess_science(CLAIM,[SOURCE],judge=Judge(payload()))
        self.assertFalse(r['certifies_scientific_accuracy']);self.assertEqual(len(r['coverage_by_window'][0]),7)
        self.assertFalse(r['issues']);self.assertEqual(r['flags'][0]['status'],'SCIENTIFIC_CONCERN')
    def test_model_failure_does_not_pass(self):
        r=assess_science(CLAIM,[SOURCE],judge=Judge({'assessments':[item()],'coverage':[]}))
        self.assertTrue(r['issues']);self.assertTrue(any(f['status']=='NEEDS_REVIEW' for f in r['flags']))
    def test_dataset_all_columns(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.csv';p.write_text('x,y\n1,\n1,\nNaN,text\n')
            r=dataset_integrity([{'id':'d','path':str(p)}])[0]
            self.assertEqual(r['duplicate_rows'],1);self.assertEqual(r['columns']['x']['nonfinite'],1)
            self.assertEqual(r['columns']['y']['missing'],2)
    def test_api_unavailable_preserves_local_checks(self):
        with patch('verifier.llm.OpenAIJudge',side_effect=ModelError('No credentials')):
            r=analyse(CLAIM,context=SCOPE,mode='hybrid')
        self.assertEqual(r['status'],'needs_review');self.assertFalse(r['api']['configured'])
        self.assertTrue(any(f['check']=='API' for f in r['flags']));self.assertIn('quantum',r)
    def test_combined_quantum_keeps_scientific_flags(self):
        r=analyse(CLAIM,context={**SCOPE,'sources':[SOURCE]},mode='hybrid',judge=Judge(payload()),
            run_citations=False,extract_claims=False)
        self.assertTrue(any(f['check']=='SCIENCE' for f in r['flags']))
        self.assertEqual(len(r['quantum']['review_indices']),sum(f['needs_human_review'] for f in r['flags']))
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):analyse('x',context=SCOPE,mode='unknown')
    def test_server_materializes_exact_passages_and_claims(self):
        x=item();x.update(claim='',claim_id='claim_0000')
        x['evidence']=[{'source_id':'s','passage_id':'s_p0_0','quote':''}]
        r=assess_science(CLAIM,[SOURCE],judge=Judge(payload(x)))
        self.assertFalse(r['issues']);self.assertEqual(r['flags'][0]['claim'],CLAIM)
        self.assertEqual(r['flags'][0]['evidence'][0]['quote'],SOURCE['text'])
    def test_invalid_passage_stays_reviewable_after_retry(self):
        x=item();x['evidence']=[{'source_id':'s','passage_id':'invented','quote':''}]
        r=assess_science(CLAIM,[SOURCE],judge=Judge(payload(x)))
        self.assertTrue(r['issues']);self.assertEqual(r['flags'][0]['status'],'NEEDS_REVIEW')

if __name__=='__main__':unittest.main()
