import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from verifier.citations import check_reference, doi_in
from verifier.llm import OpenAIJudge, ModelError
from verifier.research import independent_sources
from verifier.legal import check_legal_reference
from verifier.auto_data import extract_data_claims
from verifier.anchors import verbatim

class IntegrationTests(unittest.TestCase):
    def test_whitespace_recovery_keeps_original(self):
        self.assertEqual(verbatim('Claim continues here.','Claim continues\nhere.'),'Claim continues\nhere.')
        self.assertEqual(verbatim('Claim proves the result.','Claim suggests the result.'),'Claim proves the result.')
    def test_ambiguous_whitespace_recovery_rejected(self):
        self.assertEqual(verbatim('A B','A\nB and A\tB'),'A B')
    def test_openai_strict_output_and_no_storage(self):
        payload={'status':'NEEDS_REVIEW','reason':'missing evidence','quote':'','confidence':0,'suggested_fix':'Supply evidence'}
        client=SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(
            status='completed',output_text=json.dumps(payload),model='model-version',id='request-1',usage=None))))
        result,audit=OpenAIJudge(client=client,model='configured-model').json('Untrusted paper',dict)
        kwargs=client.responses.create.call_args.kwargs
        self.assertFalse(kwargs['store']);self.assertTrue(kwargs['text']['format']['strict'])
        self.assertEqual(result,payload);self.assertEqual(audit['request_id'],'request-1')
    def test_openai_error_does_not_leak_credentials(self):
        client=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=RuntimeError('SECRET_KEY'))))
        with self.assertRaises(ModelError) as error:OpenAIJudge(client=client).json('text',dict)
        self.assertNotIn('SECRET_KEY',str(error.exception))
    def test_balanced_doi(self):
        self.assertEqual(doi_in('doi:10.1016/S0140-6736(20)31180-6.'),'10.1016/s0140-6736(20)31180-6')
        self.assertEqual(doi_in('(doi:10.1234/abc).'),'10.1234/abc')
    def test_unrelated_hit_is_not_fake_ngo_reference(self):
        with patch('verifier.citations.candidates',return_value=[{'title':['Unrelated biomedical article'],'DOI':'10.1234/article'}]):
            self.assertEqual(check_reference('Amnesty annual report',{'title':'Amnesty annual report'})['status'],'NEEDS_REVIEW')
    def test_missing_authors_does_not_mask_wrong_exact_doi_title(self):
        with patch('verifier.citations.candidates',return_value=[{'title':['Unrelated article'],'DOI':'10.1234/article'}]):
            self.assertEqual(check_reference('Other title. doi:10.1234/article',{'title':'Other title','authors':['Author']})['status'],'MISMATCH')
    def test_retraction_notice_not_itself_retracted(self):
        hit={'title':['Retraction notice'],'DOI':'10.1234/notice','update-to':[{'type':'retraction','DOI':'10.1234/original'}]}
        with patch('verifier.citations.candidates',return_value=[hit]):
            self.assertEqual(check_reference('Retraction notice. doi:10.1234/notice',{'title':'Retraction notice'})['status'],'VERIFIED')
    def test_independent_search_bounded(self):
        for q in (['a']*4,['x'*301],[''],None):
            with self.assertRaises(ValueError):independent_sources(q)
    def test_legal_lookup_failure_abstains(self):
        with patch.dict('os.environ',{'COURTLISTENER_API_TOKEN':''}):
            self.assertEqual(check_legal_reference('Brown v. Board of Education, 347 U.S. 483 (1954)')['status'],'NEEDS_REVIEW')
    def test_automatic_numeric_link_requires_explicit_anchor(self):
        class Judge:
            def json(self,*args,**kwargs):return {'items':[{'claim':'The mean is 3.','dataset_id':'d','figure_id':'','reported':3}]},{}
        with self.assertRaises(ModelError):extract_data_claims('The mean is 3.',[{'id':'d','label':'Dataset 1'}],[],Judge())

if __name__=='__main__':unittest.main()
