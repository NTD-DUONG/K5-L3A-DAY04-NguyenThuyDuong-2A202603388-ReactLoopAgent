"""Regression tests for exceptions and interrupted tool responses; no API calls."""
import unittest

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class RobustnessTests(unittest.TestCase):
    def test_provider_exception_returns_error_trace_without_secret(self):
        class BrokenProvider:
            def complete(self, messages, schemas):
                raise RuntimeError('private-key-placeholder')

        result = run_agent('x', BrokenProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][-1]['event'], 'provider_error')
        self.assertNotIn('private-key-placeholder', str(result))

    def test_tool_timeout_is_observation_and_model_can_recover(self):
        class BrokenTools:
            def execute(self, name, args):
                raise TimeoutError('private tool diagnostics')

        provider = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"github"}'),
            final('Không kiểm tra được do timeout.'),
        ])
        result = run_agent('x', provider, BrokenTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['trace'][1]['result'],
                         {'ok': False, 'error': 'TimeoutError'})
        self.assertEqual(provider.histories[1][-1]['tool_call_id'], 'a')

    def test_truncated_tool_request_is_not_executed(self):
        class MustNotExecute:
            def execute(self, name, args):
                raise AssertionError('truncated response must not execute tools')

        response = tool_call('a', 'get_status', '{}')
        response['finish'] = 'length'
        result = run_agent('x', FakeProvider([response]), MustNotExecute())
        self.assertEqual(result['status'], 'error')
        self.assertFalse(any(e['event'] == 'tool' for e in result['trace']))


if __name__ == '__main__':
    unittest.main()
