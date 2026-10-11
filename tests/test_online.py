import unittest
from unittest.mock import patch
from verifier.online import verify
from verifier.citations import check_reference, candidates
from verifier.claims import judge_support, extract_citations, source_for
from verifier.llm import parse_json, ModelError
from verifier.http import DependencyError

REAL = {'title':['A study of valid evidence'], 'DOI':'10.1234/real',
        'author':[{'family':'Smith'}], 'published':{'date-parts':[[2020]]}}
META = {'title':'A study of valid evidence','authors':['Smith'],'year':2020}
REF = 'Smith. A study of valid evidence. 2020. doi:10.1234/real'

class Judge:
    def __init__(self, payload): self.payload = payload
    def json(self, *args, **kwargs): return self.payload, {'model':'test-double','prompt':args[0]}

class Tests(unittest.TestCase):
    def tearDown(self):
        candidates.cache_clear(); source_for.cache_clear()

    def test_fenced_json(self):
        self.assertEqual(parse_json('Here is JSON: ```json\n[{"a":1}]\n```',list), [{'a':1}])
        with self.assertRaises(ModelError): parse_json('[broken]',list)

    def test_valid_metadata(self):
        with patch('verifier.citations.candidates',return_value=[REAL]):
            self.assertEqual(check_reference(REF,META)['status'],'VERIFIED')

    def test_author_year_title_changes(self):
        with patch('verifier.citations.candidates',return_value=[REAL]):
            for change in ({'authors':['Jones']},{'year':2021},{'title':'Fake quantum miracle'}):
                self.assertEqual(check_reference(REF,META|change)['status'],'MISMATCH')

    def test_fake_and_empty_titles(self):
        with patch('verifier.citations.candidates',return_value=[]), patch('verifier.providers.fallback_candidates',return_value=([],[])):
            self.assertEqual(check_reference('Fake paper')['status'],'NOT_FOUND')
        with patch('verifier.citations.candidates',return_value=[{'title':['']} ]):
            self.assertEqual(check_reference('Fake paper')['status'],'NEEDS_REVIEW')

    def test_outage_not_fake(self):
        with patch('verifier.citations.candidates',side_effect=DependencyError('offline')), patch('verifier.providers.fallback_candidates',return_value=([],['offline'])):
            self.assertEqual(check_reference(REF)['status'],'NEEDS_REVIEW')

    def test_cache(self):
        with patch('verifier.citations.get_json',return_value={'message':REAL}) as get:
            candidates(REF); candidates(REF)
            self.assertEqual(get.call_count,1)

    def test_no_source_not_supported(self):
        self.assertEqual(judge_support('Cures cancer','')['status'],'NEEDS_REVIEW')

    def test_quote_grounding_and_confidence(self):
        payload={'status':'SUPPORTED','reason':'supported','quote':'invented passage','confidence':0.99}
        self.assertEqual(judge_support('x','actual source',Judge(payload))['status'],'NEEDS_REVIEW')
        payload.update(quote='actual source',confidence=0.5)
        self.assertEqual(judge_support('x','actual source',Judge(payload))['status'],'NEEDS_REVIEW')
        payload.update(confidence=0.9)
        self.assertEqual(judge_support('x','actual source',Judge(payload))['status'],'SUPPORTED')

    def test_distinct_verdicts(self):
        for status in ['PARTIAL','CONTRADICTED','UNSUPPORTED']:
            payload={'status':status,'reason':'check scope','quote':'source','confidence':0.9}
            self.assertEqual(judge_support('x','source',Judge(payload))['status'],status)

    def test_extraction_rejects_inventions(self):
        item={'claim':'actual claim','citation':REF,**META,'unresolved':False}
        self.assertEqual(extract_citations('actual claim '+REF,Judge([item])),[item])
        with self.assertRaises(ModelError): extract_citations('other text',Judge([item]))

    def test_pipeline_missing_abstract_and_legacy(self):
        item={'claim':'actual claim','citation':REF,**META,'unresolved':False}
        with patch('verifier.citations.candidates',return_value=[REAL]), patch('verifier.online.source_for',return_value={'text':'','retraction':'unknown'}):
            result=verify('actual claim '+REF,judge=Judge([item]))[0]
            self.assertEqual(result['status'],'NEEDS_REVIEW')
            self.assertEqual(result['citation_status'],'VERIFIED')
            result=verify('actual claim '+REF,judge=Judge([item]),legacy=True)[0]
            self.assertEqual(result['status'],'UNSUPPORTED')
            self.assertEqual(result['detailed_status'],'NEEDS_REVIEW')

    def test_unresolved_marker(self):
        item={'claim':'Claim [1].','citation':'[1]','title':'','authors':[],'year':None,'unresolved':True}
        self.assertEqual(verify('Claim [1].',judge=Judge([item]))[0]['status'],'NEEDS_REVIEW')

    def test_empty(self): self.assertEqual(verify(''),[])

if __name__=='__main__': unittest.main()
