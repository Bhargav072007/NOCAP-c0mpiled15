import unittest,tempfile,json,socket
from pathlib import Path
from unittest.mock import patch
from verifier.local import analyse,InputError
from verifier.quantum import prioritize
from verifier.local import check_reference,assess_claim,references_in

SCOPE={'org_id':'o','project_id':'p'}
class LocalTests(unittest.TestCase):
 def test_bibliography_leading_newlines(self):self.assertEqual(references_in('Claim.\n\nReferences\n\nEntry A\n\nEntry B'),['Entry A','Entry B'])
 def test_empty_quantum(self):self.assertEqual(prioritize([])['batches'],[])
 def test_grover_four_one(self):
  flags=[{'status':'NEEDS_REVIEW' if i==2 else 'VERIFIED'} for i in range(4)]
  q=prioritize(flags);b=q['batches'][0];self.assertEqual(b['iterations'],1);self.assertAlmostEqual(b['amplified_marked_probability'],1);self.assertAlmostEqual(b['observations'][2]['probability'],1)
 def test_no_marked(self):
  b=prioritize([{'status':'VERIFIED'}]*3)['batches'][0];self.assertEqual(b['iterations'],0);self.assertEqual(b['amplified_marked_probability'],0);self.assertAlmostEqual(b['padded_probability'],.25)
 def test_multiple_endian(self):
  q=prioritize([{'status':'NEEDS_REVIEW' if i in (1,6) else 'VERIFIED'} for i in range(8)]);b=q['batches'][0];self.assertAlmostEqual(b['amplified_marked_probability'],1);self.assertEqual(b['marked_indices'],[1,6])
 def test_batched_no_drops(self):
  q=prioritize([{'status':'NEEDS_REVIEW'}]*270);self.assertEqual(len(q['review_indices']),270);self.assertEqual(sum(len(b['observations']) for b in q['batches']),270)
 def test_bad_shots(self):
  with self.assertRaises(ValueError):prioritize([],0)
 def test_missing_is_not_fake(self):self.assertEqual(check_reference('Unknown',[])['status'],'NEEDS_REVIEW')
 def test_catalog_unreviewed(self):self.assertEqual(check_reference('X',[{'id':'r','reference':'X','status':'VERIFIED','source_url':'url'}])['status'],'NEEDS_REVIEW')
 def test_catalog_ambiguity(self):
  record={'id':'r','reference':'X','status':'VERIFIED','source_url':'url','reviewed':True};self.assertEqual(check_reference('X',[record,record])['status'],'NEEDS_REVIEW')
 def test_quotes_no_entailment(self):
  source={'id':'s','text':'Some outcomes improve.','identity_reviewed':True,'source_url':'url'}
  self.assertEqual(assess_claim({'claim':'All outcomes improve.','source_id':'s','quote':source['text']},{'s':source})['status'],'NEEDS_REVIEW')
 def test_exact_quote(self):
  source={'id':'s','text':'Some outcomes improve.','identity_reviewed':True,'source_url':'url'}
  self.assertEqual(assess_claim({'claim':source['text'],'source_id':'s','quote':source['text']},{'s':source})['status'],'VERIFIED')
 def test_invalid_quote(self):self.assertEqual(assess_claim({'claim':'x','source_id':'s','quote':'invented'},{'s':{'id':'s','text':'actual'}})['status'],'NEEDS_REVIEW')
 def test_unknown_claim_rejected(self):
  with self.assertRaises(InputError):analyse('Paper',context={**SCOPE,'claims':[{'claim':'Invented'}]})
 def test_duplicate_ids_rejected(self):
  with self.assertRaises(InputError):analyse('Paper',context={**SCOPE,'catalog':[{'id':'x'},{'id':'x'}]})
 def test_all_sources_accounted(self):
  r=analyse('Paper',context={**SCOPE,'sources':[{'id':'unused','text':'Evidence'}]});self.assertTrue(any(f.get('source_id')=='unused' for f in r['flags']))
 def test_data_and_unassessed_columns(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.csv';p.write_text('a,b\n1,3\n2,4\n3,5\n')
   ctx={**SCOPE,'datasets':[dict(SCOPE,id='d',path=str(p))],'claims':[{'claim':'The mean is 8.','dataset_id':'d','column':'a','metric':'mean','reported':8}]}
   r=analyse('The mean is 8.',context=ctx);self.assertIn('DATA_MISMATCH',r['summary']);self.assertEqual(r['dataset_inventory'][0]['unassessed_columns'],['b'])
 def test_offline(self):
  with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')),patch.object(socket,'getaddrinfo',side_effect=AssertionError('network forbidden')):
   r=analyse('References\n\nUnknown author. (2024). Unknown title.',context=SCOPE)
  self.assertEqual(r['network_requests'],0);self.assertEqual(r['flags'][0]['status'],'NEEDS_REVIEW')
if __name__=='__main__':unittest.main()
