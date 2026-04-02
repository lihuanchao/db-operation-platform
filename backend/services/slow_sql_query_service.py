class SlowSqlQueryService:
    LIST_BASE_SQL = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
    LEFT JOIN monitor_mysql_slow_query_optimized m ON a.checksum = m.checksum
WHERE
    c.host IS NOT NULL
    AND c.port IS NOT NULL
    AND c.is_delete != 1
    AND a.sample != 'commit'
    AND (b.db_max != 'information_schema' OR b.db_max IS NULL)
    AND b.user_max IS NOT NULL
"""

    DETAIL_BASE_SQL = """
SELECT
    a.checksum,
    c.host,
    b.db_max AS database_name,
    b.user_max,
    a.sample,
    a.last_seen,
    SUM(b.ts_cnt) AS execution_count,
    SUM(b.Query_time_sum) / SUM(b.ts_cnt) AS avg_time,
    MAX(b.Query_time_max) AS max_time,
    MIN(b.Query_time_min) AS min_time,
    SUM(b.Query_time_sum) AS total_time
FROM
    monitor_mysql_slow_query_review a
    LEFT JOIN monitor_mysql_slow_query_review_history b ON a.checksum = b.checksum
    LEFT JOIN db_resource c ON b.resid_max = c.res_id
WHERE
    a.checksum = :checksum
"""

    @staticmethod
    def build_host_scope(allowed_hosts):
        if allowed_hosts is None:
            return '', {}

        normalized_hosts = [host for host in allowed_hosts if host]
        if not normalized_hosts:
            normalized_hosts = ['__no_authorized_host__']

        placeholders = ', '.join(
            f':allowed_host_{index}' for index, _ in enumerate(normalized_hosts)
        )
        params = {
            f'allowed_host_{index}': host for index, host in enumerate(normalized_hosts)
        }
        return f' AND c.host IN ({placeholders})', params

    @classmethod
    def build_list_query(cls, filters, allowed_hosts=None):
        sql = cls.LIST_BASE_SQL
        params = {}

        host_scope_sql, host_scope_params = cls.build_host_scope(allowed_hosts)
        sql += host_scope_sql
        params.update(host_scope_params)

        if filters.get('host'):
            sql += ' AND c.host = :host'
            params['host'] = filters['host']

        if filters.get('database_name'):
            sql += ' AND b.db_max = :database_name'
            params['database_name'] = filters['database_name']

        is_optimized = filters.get('is_optimized')
        if is_optimized == '1':
            sql += ' AND m.is_optimized = 1'
        elif is_optimized == '0':
            sql += ' AND (m.is_optimized = 0 OR m.is_optimized IS NULL)'

        if filters.get('ts_min') and filters.get('ts_max'):
            sql += ' AND b.ts_min > :ts_min AND b.ts_max < :ts_max'
            params['ts_min'] = filters['ts_min']
            params['ts_max'] = filters['ts_max']

        sql += """
GROUP BY
    a.checksum
ORDER BY
    SUM(b.Query_time_sum) DESC
"""
        return sql, params

    @classmethod
    def build_detail_query(cls, checksum, allowed_hosts=None):
        sql = cls.DETAIL_BASE_SQL
        params = {'checksum': checksum}

        host_scope_sql, host_scope_params = cls.build_host_scope(allowed_hosts)
        sql += host_scope_sql
        params.update(host_scope_params)

        sql += """
GROUP BY
    a.checksum
"""
        return sql, params
