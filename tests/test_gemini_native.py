"""Verify native translation and preservation of tool-call thought signatures."""
import json
import unittest
from unittest.mock import patch

from providers import Provider
from status_tools import SCHEMAS


class GeminiNativeTests(unittest.TestCase):
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy', 'GEMINI_API_MODE': 'native'})
    @patch('providers.post_json')
    def test_tool_round_trip_preserves_signature_and_usage(self, post):
        parts = [{
            'functionCall': {'name': 'get_status', 'args': {'provider': 'github'}},
            'thoughtSignature': 'opaque-signature',
        }]
        post.side_effect = [
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': parts}}],
             'usageMetadata': {'totalTokenCount': 12}},
            {'candidates': [{'finishReason': 'STOP',
                             'content': {'parts': [{'text': 'Done'}]}}]},
        ]
        client = Provider('gemini', 'test-model')
        messages = [{'role': 'system', 'content': 'system'},
                    {'role': 'user', 'content': 'question'}]
        first = client.complete(messages, SCHEMAS)
        self.assertEqual(first['finish'], 'tool_calls')
        self.assertEqual(first['usage']['totalTokenCount'], 12)
        messages += [first['message'], {
            'role': 'tool', 'tool_call_id': first['calls'][0]['id'],
            'content': json.dumps({'provider': 'github'}),
        }]
        second = client.complete(messages, SCHEMAS)
        self.assertEqual(second['finish'], 'stop')
        self.assertEqual(second['message']['content'], 'Done')
        url, headers, payload = post.call_args.args
        self.assertTrue(url.endswith('/test-model:generateContent'))
        self.assertEqual(headers, {'x-goog-api-key': 'dummy'})
        self.assertEqual(payload['contents'][1]['parts'], parts)
        response = payload['contents'][2]['parts'][0]['functionResponse']
        self.assertEqual(response['name'], 'get_status')
        self.assertEqual(response['response'], {'provider': 'github'})
        self.assertNotIn('additionalProperties',
                         payload['tools'][0]['functionDeclarations'][0]['parameters'])


if __name__ == '__main__':
    unittest.main()
