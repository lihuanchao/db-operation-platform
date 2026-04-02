import unittest

from services.slow_sql_query_service import SlowSqlQueryService


class SlowSqlQueryServiceTestCase(unittest.TestCase):
    def test_build_list_query_adds_manage_host_scope_for_normal_user(self):
        sql, params = SlowSqlQueryService.build_list_query(
            filters={'database_name': '', 'host': '', 'is_optimized': ''},
            allowed_hosts=['10.0.0.11', '10.0.0.21']
        )
        self.assertIn('c.host IN (:allowed_host_0, :allowed_host_1)', sql)
        self.assertEqual(params['allowed_host_0'], '10.0.0.11')
        self.assertEqual(params['allowed_host_1'], '10.0.0.21')

    def test_build_list_query_skips_manage_host_scope_for_admin(self):
        sql, params = SlowSqlQueryService.build_list_query(
            filters={'database_name': '', 'host': '', 'is_optimized': ''},
            allowed_hosts=None
        )
        self.assertNotIn('allowed_host_0', sql)
        self.assertNotIn('allowed_host_0', params)

    def test_build_detail_query_reuses_authorized_host_scope(self):
        sql, params = SlowSqlQueryService.build_detail_query('abc123', allowed_hosts=['10.0.0.11'])
        self.assertIn('a.checksum = :checksum', sql)
        self.assertIn('c.host IN (:allowed_host_0)', sql)
        self.assertEqual(params['checksum'], 'abc123')


if __name__ == '__main__':
    unittest.main()
