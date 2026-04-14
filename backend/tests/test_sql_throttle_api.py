import os
import unittest
from unittest.mock import patch

os.environ['USE_SQLITE'] = 'true'
os.environ['SECRET_KEY'] = 'sql-throttle-secret'
os.environ['SKIP_SCHEDULER_INIT'] = '1'

from app import app
from extensions import db
from models.db_connection import DbConnection
from models.sys_user import SysUser
from services.auth_service import AuthService


class SqlThrottleApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='sql-throttle-secret')
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        self.admin = SysUser(
            employee_no='A2001',
            password_hash=AuthService.hash_password('Passw0rd!'),
            real_name='管理员',
            department='DBA',
            role_code='admin',
            status='enabled',
        )
        self.connection = DbConnection(
            id=1,
            connection_name='限流测试连接',
            host='127.0.0.1',
            manage_host='127.0.0.1',
            port=3306,
            username='platform_user',
            password='secret',
            is_enabled=1,
        )
        db.session.add_all([self.admin, self.connection])
        db.session.commit()

        login_response = self.client.post('/api/auth/login', json={
            'employee_no': 'A2001',
            'password': 'Passw0rd!',
        })
        self.assertEqual(login_response.status_code, 200)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _create_rule(self, **overrides):
        payload = {
            'rule_name': '订单表限流',
            'db_connection_id': self.connection.id,
            'slow_sql_seconds': 1,
            'fingerprint_concurrency_threshold': 2,
            'poll_interval_seconds': 15,
            'max_kill_per_round': 5,
            'consecutive_hit_times': 1,
            'dry_run': True,
            'enabled': True,
            'exclude_users': ['replication'],
            'exclude_hosts': [],
            'exclude_dbs': [],
            'exclude_fingerprints': [],
        }
        payload.update(overrides)
        response = self.client.post('/api/sql-throttle-rules', json=payload)
        self.assertEqual(response.status_code, 200)
        return response.get_json()['data']

    @staticmethod
    def _mock_sessions():
        return {
            'mysql_version': '8.0.36',
            'collector_mode': 'information_schema',
            'sample_time': '2026-04-14 12:00:00',
            'sessions': [
                {
                    'thread_id': 101,
                    'process_id': 101,
                    'user': 'app_user',
                    'host': '10.0.0.1:3306',
                    'db': 'order_db',
                    'command': 'Query',
                    'state': 'Sending data',
                    'exec_time_seconds': 12,
                    'sql_text': "select * from orders where user_id = 1001 and status = 'paid'",
                    'digest': None,
                    'sample_time': '2026-04-14 12:00:00',
                },
                {
                    'thread_id': 102,
                    'process_id': 102,
                    'user': 'app_user',
                    'host': '10.0.0.2:3306',
                    'db': 'order_db',
                    'command': 'Query',
                    'state': 'Sending data',
                    'exec_time_seconds': 18,
                    'sql_text': "select * from orders where user_id = 1002 and status = 'paid'",
                    'digest': None,
                    'sample_time': '2026-04-14 12:00:00',
                },
            ],
        }

    def test_create_sql_throttle_rule_and_defaults(self):
        response = self.client.post('/api/sql-throttle-rules', json={
            'rule_name': '支付订单限流',
            'db_connection_id': self.connection.id,
            'slow_sql_seconds': 10,
            'fingerprint_concurrency_threshold': 20,
            'poll_interval_seconds': 15,
            'max_kill_per_round': 10,
            'consecutive_hit_times': 2,
        })

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        data = body['data']
        self.assertEqual(data['rule_name'], '支付订单限流')
        self.assertEqual(data['kill_command'], 'KILL QUERY')
        self.assertTrue(data['dry_run'])
        self.assertFalse(data['enabled'])

    def test_run_once_in_dry_run_creates_kill_logs_without_kill_query(self):
        rule = self._create_rule(dry_run=True, consecutive_hit_times=1)

        with patch('services.mysql_session_collector.MysqlSessionCollector.collect_active_sessions', return_value=self._mock_sessions()):
            response = self.client.post(f"/api/sql-throttle-rules/{rule['id']}/run-once")

        self.assertEqual(response.status_code, 200)
        run = response.get_json()['data']
        self.assertEqual(run['status'], 'completed')
        self.assertEqual(run['candidate_fingerprint_count'], 1)
        self.assertEqual(run['hit_fingerprint_count'], 1)
        self.assertEqual(run['kill_attempt_count'], 2)
        self.assertEqual(run['kill_success_count'], 0)

        kill_logs_response = self.client.get(f"/api/sql-throttle-runs/{run['id']}/kill-logs")
        self.assertEqual(kill_logs_response.status_code, 200)
        kill_logs = kill_logs_response.get_json()['data']['items']
        self.assertEqual(len(kill_logs), 2)
        self.assertTrue(all(item['kill_result'] == 'dry_run' for item in kill_logs))

    def test_consecutive_hit_requires_multiple_rounds(self):
        rule = self._create_rule(dry_run=True, consecutive_hit_times=2)

        with patch('services.mysql_session_collector.MysqlSessionCollector.collect_active_sessions', return_value=self._mock_sessions()):
            first_response = self.client.post(f"/api/sql-throttle-rules/{rule['id']}/run-once")
            second_response = self.client.post(f"/api/sql-throttle-rules/{rule['id']}/run-once")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        first_run = first_response.get_json()['data']
        second_run = second_response.get_json()['data']

        self.assertEqual(first_run['hit_fingerprint_count'], 0)
        self.assertEqual(first_run['kill_attempt_count'], 0)
        self.assertEqual(second_run['hit_fingerprint_count'], 1)
        self.assertEqual(second_run['kill_attempt_count'], 2)

    def test_execution_logs_support_sql_throttle_types(self):
        rule = self._create_rule(dry_run=True, consecutive_hit_times=1)

        with patch('services.mysql_session_collector.MysqlSessionCollector.collect_active_sessions', return_value=self._mock_sessions()):
            run_response = self.client.post(f"/api/sql-throttle-rules/{rule['id']}/run-once")
        run_id = run_response.get_json()['data']['id']

        run_log_response = self.client.get('/api/execution-logs?log_type=sql_throttle_run&page=1&per_page=10')
        self.assertEqual(run_log_response.status_code, 200)
        run_items = run_log_response.get_json()['data']['items']
        self.assertEqual(len(run_items), 1)
        self.assertEqual(run_items[0]['log_type'], 'sql_throttle_run')
        self.assertEqual(run_items[0]['id'], run_id)

        kill_log_response = self.client.get('/api/execution-logs?log_type=sql_kill&page=1&per_page=10')
        self.assertEqual(kill_log_response.status_code, 200)
        kill_items = kill_log_response.get_json()['data']['items']
        self.assertEqual(len(kill_items), 2)
        self.assertEqual(kill_items[0]['log_type'], 'sql_kill')

        merged_response = self.client.get('/api/execution-logs?log_type=all&page=1&per_page=10')
        self.assertEqual(merged_response.status_code, 200)
        merged_types = {item['log_type'] for item in merged_response.get_json()['data']['items']}
        self.assertIn('sql_throttle_run', merged_types)
        self.assertIn('sql_kill', merged_types)

    def test_typed_execution_log_content_supports_sql_throttle_logs(self):
        rule = self._create_rule(dry_run=True, consecutive_hit_times=1)
        with patch('services.mysql_session_collector.MysqlSessionCollector.collect_active_sessions', return_value=self._mock_sessions()):
            run_response = self.client.post(f"/api/sql-throttle-rules/{rule['id']}/run-once")
        run_id = run_response.get_json()['data']['id']
        kill_logs = self.client.get(f"/api/sql-throttle-runs/{run_id}/kill-logs").get_json()['data']['items']
        kill_id = kill_logs[0]['id']

        run_log_content = self.client.get(f'/api/execution-logs/sql_throttle_run/{run_id}/log-content')
        self.assertEqual(run_log_content.status_code, 200)
        self.assertIn('run_id', run_log_content.get_json()['data']['content'])

        kill_log_content = self.client.get(f'/api/execution-logs/sql_kill/{kill_id}/log-content')
        self.assertEqual(kill_log_content.status_code, 200)
        self.assertIn('thread_id', kill_log_content.get_json()['data']['content'])

    def test_run_list_supports_rule_name_and_hit_filters(self):
        hit_rule = self._create_rule(
            rule_name='目标规则A',
            dry_run=True,
            consecutive_hit_times=1,
            fingerprint_concurrency_threshold=2,
        )
        miss_rule = self._create_rule(
            rule_name='其他规则B',
            dry_run=True,
            consecutive_hit_times=1,
            fingerprint_concurrency_threshold=3,
        )

        with patch('services.mysql_session_collector.MysqlSessionCollector.collect_active_sessions', return_value=self._mock_sessions()):
            self.client.post(f"/api/sql-throttle-rules/{hit_rule['id']}/run-once")
            self.client.post(f"/api/sql-throttle-rules/{miss_rule['id']}/run-once")

        by_name = self.client.get('/api/sql-throttle-runs?rule_name=目标规则A&page=1&per_page=10')
        self.assertEqual(by_name.status_code, 200)
        by_name_items = by_name.get_json()['data']['items']
        self.assertGreaterEqual(len(by_name_items), 1)
        self.assertTrue(all(item['rule_name'] == '目标规则A' for item in by_name_items))

        hit_only = self.client.get('/api/sql-throttle-runs?is_hit=true&page=1&per_page=10')
        self.assertEqual(hit_only.status_code, 200)
        hit_only_items = hit_only.get_json()['data']['items']
        self.assertGreaterEqual(len(hit_only_items), 1)
        self.assertTrue(all(item['hit_fingerprint_count'] > 0 for item in hit_only_items))

        miss_only = self.client.get('/api/sql-throttle-runs?is_hit=false&page=1&per_page=10')
        self.assertEqual(miss_only.status_code, 200)
        miss_only_items = miss_only.get_json()['data']['items']
        self.assertGreaterEqual(len(miss_only_items), 1)
        self.assertTrue(all(item['hit_fingerprint_count'] == 0 for item in miss_only_items))


if __name__ == '__main__':
    unittest.main()
