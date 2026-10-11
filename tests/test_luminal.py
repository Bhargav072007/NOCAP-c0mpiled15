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
        self.assertTrue(call.kwargs['json']['response_format']['json_schema']['strict'])
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
