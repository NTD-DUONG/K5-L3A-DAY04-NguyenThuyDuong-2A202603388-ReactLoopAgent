"""Offline retry-budget and pagination regression tests."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest

from bonus.tools import BonusTools
from bonus_policy import BonusExecutionPolicy


class PolicyTests(unittest.TestCase):
    def test_persistent_rate_limit_stops_after_three_real_attempts(self):
        raw = BonusTools(scenario='rate_limit_always')
        tools = BonusExecutionPolicy(raw)
        results = [tools.execute('get_vercel_status', {}) for _ in range(4)]
        self.assertTrue(results[0]['retry_allowed'])
        self.assertFalse(results[2]['retry_allowed'])
        self.assertEqual(results[3]['error'], 'RETRY_LIMIT_REACHED')
        self.assertEqual(raw.calls[('get_vercel_status', 'vercel')], 3)
        self.assertEqual(tools.execute('get_github_status', {})['provider'], 'github')

    def test_transient_rate_limit_recovers_without_sleep_in_simulation(self):
        sleeps = []
        tools = BonusExecutionPolicy(BonusTools(scenario='rate_limit_once'), sleep=sleeps.append)
        self.assertEqual(tools.execute('get_vercel_status', {})['error'], 'RATE_LIMITED')
        self.assertEqual(tools.execute('get_vercel_status', {})['provider'], 'vercel')
        self.assertEqual(sleeps, [])

    def test_retry_after_is_honored_before_another_request(self):
        clock = [0.0]
        sleeps = []

        class Tools:
            schemas = []
            system_prompt = ''

            def execute(self, name, args):
                if not sleeps:
                    return {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '2'}
                return {'ok': True}

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        tools = BonusExecutionPolicy(Tools(), sleep=sleep, monotonic=lambda: clock[0])
        self.assertTrue(tools.execute('status', {})['retry_allowed'])
        self.assertTrue(tools.execute('status', {})['ok'])
        self.assertEqual(sleeps, [2.0])

    def test_long_retry_after_halts_without_sleep_or_extra_request(self):
        class Tools:
            schemas = []
            system_prompt = ''
            calls = 0

            def execute(self, name, args):
                self.calls += 1
                return {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '120'}

        raw = Tools()
        sleeps = []
        tools = BonusExecutionPolicy(raw, sleep=sleeps.append)
        self.assertFalse(tools.execute('status', {})['retry_allowed'])
        self.assertEqual(tools.execute('status', {})['error'], 'RETRY_LIMIT_REACHED')
        self.assertEqual(raw.calls, 1)
        self.assertEqual(sleeps, [])

    def test_http_date_retry_after_is_parsed(self):
        date = format_datetime(datetime.now(timezone.utc) + timedelta(days=1), usegmt=True)
        seconds = BonusExecutionPolicy._retry_delay({'retry_after': date}, 1)
        self.assertGreater(seconds, 86000)

    def test_pagination_remains_available_after_success(self):
        raw = BonusTools()
        tools = BonusExecutionPolicy(raw)
        first = tools.execute('get_incident_details', {
            'provider': 'vercel', 'incident_id': 'sps6n39gm4sg', 'offset': 0, 'limit': 3,
        })
        second = tools.execute('get_incident_details', {
            'provider': 'vercel', 'incident_id': first['id'],
            'offset': first['next_offset'], 'limit': 3,
        })
        self.assertEqual(second['offset'], 3)
        self.assertTrue(any('GitHub' in update['body'] for update in second['updates']))
        self.assertEqual(second['total_updates'], first['total_updates'])


if __name__ == '__main__':
    unittest.main()
