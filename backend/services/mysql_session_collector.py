from datetime import datetime

import pymysql


class MysqlSessionCollector:
    PERFORMANCE_SCHEMA_QUERY = """
        SELECT
            t.PROCESSLIST_ID AS process_id,
            t.PROCESSLIST_ID AS thread_id,
            t.PROCESSLIST_USER AS user,
            t.PROCESSLIST_HOST AS host,
            t.PROCESSLIST_DB AS db,
            t.PROCESSLIST_COMMAND AS command,
            t.PROCESSLIST_STATE AS state,
            COALESCE(t.PROCESSLIST_TIME, 0) AS exec_time_seconds,
            COALESCE(t.PROCESSLIST_INFO, '') AS sql_text
        FROM performance_schema.threads t
        WHERE t.PROCESSLIST_ID IS NOT NULL
    """

    INFORMATION_SCHEMA_QUERY = """
        SELECT
            p.ID AS process_id,
            p.ID AS thread_id,
            p.USER AS user,
            p.HOST AS host,
            p.DB AS db,
            p.COMMAND AS command,
            p.STATE AS state,
            COALESCE(p.TIME, 0) AS exec_time_seconds,
            COALESCE(p.INFO, '') AS sql_text
        FROM information_schema.processlist p
    """

    @classmethod
    def collect_active_sessions(cls, db_connection):
        with cls._open_connection(db_connection) as conn:
            version = cls._detect_version(conn)
            sample_time = datetime.now()

            sessions = []
            collector_mode = 'performance_schema'
            try:
                sessions = cls._query_dict_rows(conn, cls.PERFORMANCE_SCHEMA_QUERY)
            except Exception:
                collector_mode = 'information_schema'
                try:
                    sessions = cls._query_dict_rows(conn, cls.INFORMATION_SCHEMA_QUERY)
                except Exception:
                    collector_mode = 'processlist'
                    sessions = cls._query_show_processlist(conn)

            normalized = [cls._normalize_row(row, sample_time) for row in sessions]
            return {
                'mysql_version': version,
                'collector_mode': collector_mode,
                'sessions': normalized,
                'sample_time': sample_time.strftime('%Y-%m-%d %H:%M:%S'),
            }

    @staticmethod
    def _open_connection(db_connection):
        return pymysql.connect(
            host=db_connection.host,
            port=int(db_connection.port),
            user=db_connection.username,
            password=db_connection.password,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    @staticmethod
    def _detect_version(conn):
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION() AS version')
            row = cursor.fetchone() or {}
            return str(row.get('version') or '')

    @staticmethod
    def _query_dict_rows(conn, query):
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall() or []

    @staticmethod
    def _query_show_processlist(conn):
        rows = []
        with conn.cursor() as cursor:
            cursor.execute('SHOW FULL PROCESSLIST')
            for item in cursor.fetchall() or []:
                rows.append({
                    'process_id': item.get('Id'),
                    'thread_id': item.get('Id'),
                    'user': item.get('User'),
                    'host': item.get('Host'),
                    'db': item.get('db'),
                    'command': item.get('Command'),
                    'state': item.get('State'),
                    'exec_time_seconds': item.get('Time'),
                    'sql_text': item.get('Info'),
                })
        return rows

    @staticmethod
    def _normalize_row(row, sample_time):
        process_id = row.get('process_id') or row.get('thread_id') or 0
        thread_id = row.get('thread_id') or row.get('process_id') or 0
        exec_time = row.get('exec_time_seconds')
        try:
            exec_time_seconds = int(exec_time or 0)
        except (TypeError, ValueError):
            exec_time_seconds = 0

        return {
            'thread_id': int(thread_id or 0),
            'process_id': int(process_id or 0),
            'user': (row.get('user') or '').strip(),
            'host': (row.get('host') or '').strip(),
            'db': (row.get('db') or '').strip(),
            'command': (row.get('command') or '').strip(),
            'state': (row.get('state') or '').strip(),
            'exec_time_seconds': exec_time_seconds,
            'sql_text': (row.get('sql_text') or '').strip(),
            'digest': None,
            'sample_time': sample_time.strftime('%Y-%m-%d %H:%M:%S'),
        }
