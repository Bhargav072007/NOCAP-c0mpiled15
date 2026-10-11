import os, unittest
from unittest.mock import Mock, patch
from verifier.llm import LuminalJudge, ModelError, get_judge, SUPPORT_SCHEMA

class LuminalTests(unittest.TestCase):
    def judge(self,payload=None,status=200):
        session=Mock();session.post.return_value.status_code=status
        session.post.return_value.json.return_value=payload
        with patch.dict(os.environ,{'LUMINAL_API_KEY':'test-secret'}):
            return LuminalJudge(session=session),session
    def payload(self,content,finish='stop'):
        return {'choices':[{'message':{'content':content},'finish_reason':finish}],'id':'test','model':'test-model'}
    def test_valid(self):
        j,s=self.judge(self.payload('{"items":[]}'))
        result,a=j.json('empty',list)
        self.assertEqual(result,[]);self.assertEqual(a['provider'],'Luminal')
        call=s.post.call_args
        self.assertFalse(call.kwargs['allow_redirects'])
        self.assertEqual(call.kwargs['json']['response_format'],{'type':'json_object'})
        self.assertEqual(call.kwargs['json']['thinking'],{'type':'disabled'})
        self.assertEqual(call.args[0],'https://flash.luminal.cloud/v1/chat/completions')
    def test_invalid_schema(self):
        j,_=self.judge(self.payload('{"items":[{"claim":"invented"}]}'))
        with self.assertRaises(ModelError):j.json('x',list)
    def test_truncated(self):
        j,_=self.judge(self.payload('{"items":[]}', 'length'))
        with self.assertRaises(ModelError):j.json('x',list)
    def test_auth_error_redacted(self):
        j,_=self.judge(status=401)
        with self.assertRaises(ModelError) as error:j.json('x',list)
        self.assertIn('401',str(error.exception));self.assertNotIn('test-secret',str(error.exception))
    def test_no_redirect(self):
        j,_=self.judge(status=302)
        with self.assertRaises(ModelError):j.json('x',list)
    def test_provider_selection(self):
        with patch.dict(os.environ,{'NOCAP_PROVIDER':'luminal','LUMINAL_API_KEY':'test-secret'}):
            self.assertIsInstance(get_judge(),LuminalJudge)
        with self.assertRaises(ModelError):get_judge('invalid')
    def test_non_json(self):
        j,_=self.judge(self.payload('not JSON'))
        with self.assertRaises(ModelError):j.json('x',list)
    def test_extra_fields(self):
        j,_=self.judge(self.payload('{"items":[],"extra":true}'))
        with self.assertRaises(ModelError):j.json('x',list)
    def test_json_mode_fallback(self):
        j,s=self.judge()
        j.response_format="json_schema"
        bad=Mock(status_code=400)
        bad.json.return_value={'error':{'message':'This response_format type is unavailable now'}}
        good=Mock(status_code=200)
        good.json.return_value=self.payload('{"items":[]}')
        s.post.side_effect=[bad,good]
        result,a=j.json('empty',list)
        self.assertEqual(result,[]);self.assertEqual(a['response_format'],'json_object')
        self.assertEqual(s.post.call_args.kwargs['json']['response_format'],{'type':'json_object'})
    def test_unrelated_error_not_retried(self):
        j,s=self.judge(status=400)
        s.post.return_value.json.return_value={'error':{'message':'invalid model'}}
        with self.assertRaises(ModelError):j.json('x',list)
        self.assertEqual(s.post.call_count,1)

    def test_transient_retry(self):
        j,s=self.judge()
        bad=Mock(status_code=503);good=Mock(status_code=200)
        good.json.return_value=self.payload('{"items":[]}')
        s.post.side_effect=[bad,good]
        with patch('verifier.llm.time.sleep'):
            result,a=j.json('empty',list)
        self.assertEqual(len(a['attempts']),2)
        self.assertEqual(a['attempts'][0]['status'],503)
    def test_transient_failure_bounded(self):
        j,s=self.judge(status=503)
        with patch('verifier.llm.time.sleep'):
            with self.assertRaises(ModelError) as error:j.json('x',list)
        self.assertEqual(s.post.call_count,2)
        self.assertIn('temporarily unavailable',str(error.exception))
    def test_budget_cap(self):
        j,s=self.judge(self.payload('{"items":[]}'))
        j.json('x',list,max_tokens=6500)
        self.assertEqual(s.post.call_args.kwargs['json']['max_tokens'],4096)
    def test_nonfinite_rejected(self):
        from verifier.llm import validate_schema
        with self.assertRaises(ModelError):validate_schema(float('nan'),{'type':'number'})
    def test_invalid_configuration(self):
        for config in ({'LUMINAL_THINKING':'invalid'}, {'LUMINAL_MAX_OUTPUT_TOKENS':'oops'},
                       {'LUMINAL_MAX_OUTPUT_TOKENS':'0'}, {'LUMINAL_RESPONSE_FORMAT':'invalid'}):
            with patch.dict(os.environ,{'LUMINAL_API_KEY':'test-secret',**config}):
                with self.assertRaises(ModelError):LuminalJudge()
