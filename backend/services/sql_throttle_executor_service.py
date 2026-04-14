from collections import defaultdict
from datetime import datetime

import pymysql

from extensions import db
from models import DbConnection
from models.sql_throttle_fingerprint_state import SqlThrottleFingerprintState
from models.sql_throttle_kill_log import SqlThrottleKillLog
from models.sql_throttle_run import SqlThrottleRun
from services.mysql_session_collector import MysqlSessionCollector
from services.sql_fingerprint_service import SqlFingerprintService


class SqlThrottleExecutorService:
    DEFAULT_EXCLUDE_USERS = {
        'system user',
        'replication',
        'repl',
        'backup',
        'monitor',
        'mysqld_exporter',
    }
    EXCLUDE_COMMANDS = {'', 'Sleep', 'Connect', 'Binlog Dump', 'Binlog Dump GTID', 'Daemon'}
    TARGET_COMMANDS = {'Query', 'Execute'}

    @classmethod
    def execute_rule(cls, rule, trigger_source='scheduler'):
        run = SqlThrottleRun(
            rule_id=rule.id,
            status='running',
            dry_run=1 if rule.dry_run else 0,
            sample_started_at=datetime.now(),
        )
        db.session.add(run)
        rule.status = 'running'
        rule.last_error_message = None
        db.session.flush()

        try:
            db_connection = db.session.get(DbConnection, rule.db_connection_id)
            if not db_connection or db_connection.is_enabled == 0:
                raise ValueError('数据库连接不存在或已禁用')

            collected = MysqlSessionCollector.collect_active_sessions(db_connection)
            rule.connection_name = db_connection.connection_name
            rule.mysql_version = collected.get('mysql_version') or rule.mysql_version

            prepared_sessions = cls._prepare_sessions(rule, db_connection, collected.get('sessions') or [])
            grouped = cls._group_by_fingerprint(prepared_sessions)
            candidates = cls._pick_candidates(rule, grouped)
            states = cls._update_fingerprint_states(rule, candidates)
            hits = [item for item in candidates if states.get(item['fingerprint_hash'], 0) >= rule.consecutive_hit_times]

            kill_attempt_count, kill_success_count, kill_logs = cls._handle_hits(
                rule=rule,
                run=run,
                db_connection=db_connection,
                hit_groups=hits,
                trigger_source=trigger_source,
            )

            run.total_session_count = len(prepared_sessions)
            run.candidate_fingerprint_count = len(candidates)
            run.hit_fingerprint_count = len(hits)
            run.kill_attempt_count = kill_attempt_count
            run.kill_success_count = kill_success_count
            run.status = 'completed'
            run.sample_finished_at = datetime.now()
            run.error_message = None
            run.set_snapshot({
                'collector_mode': collected.get('collector_mode'),
                'mysql_version': collected.get('mysql_version'),
                'sample_time': collected.get('sample_time'),
                'trigger_source': trigger_source,
                'candidate_fingerprints': candidates,
                'hit_fingerprints': hits,
                'kill_logs': kill_logs,
            })

            now = datetime.now()
            rule.last_run_at = now
            if hits:
                rule.last_hit_at = now
            rule.status = 'idle'

            db.session.commit()
            return run, None
        except Exception as exc:
            db.session.rollback()
            run = db.session.get(SqlThrottleRun, run.id) if run.id else run
            if run:
                run.status = 'failed'
                run.sample_finished_at = datetime.now()
                run.error_message = str(exc)
            persisted_rule = db.session.get(type(rule), rule.id)
            if persisted_rule:
                persisted_rule.status = 'error'
                persisted_rule.last_error_message = str(exc)
                persisted_rule.last_run_at = datetime.now()
            db.session.commit()
            return None, str(exc)

    @classmethod
    def _prepare_sessions(cls, rule, db_connection, sessions):
        prepared = []
        for session in sessions:
            if not cls._is_target_session(session):
                continue
            if session['exec_time_seconds'] < int(rule.slow_sql_seconds):
                continue
            if cls._is_filtered_by_targets(rule, session):
                continue
            if cls._is_whitelisted(rule, db_connection, session):
                continue

            fingerprint, fingerprint_hash = SqlFingerprintService.fingerprint(session['sql_text'])
            if not fingerprint:
                continue
            session_item = dict(session)
            session_item['fingerprint'] = fingerprint
            session_item['fingerprint_hash'] = fingerprint_hash
            prepared.append(session_item)
        return prepared

    @classmethod
    def _is_target_session(cls, session):
        command = (session.get('command') or '').strip()
        sql_text = (session.get('sql_text') or '').strip()
        if not sql_text:
            return False
        if command in cls.EXCLUDE_COMMANDS:
            return False
        if command and command not in cls.TARGET_COMMANDS:
            return False
        if sql_text.upper().startswith('KILL '):
            return False
        return True

    @staticmethod
    def _is_filtered_by_targets(rule, session):
        target_db_pattern = (rule.target_db_pattern or '').strip()
        target_user_pattern = (rule.target_user_pattern or '').strip()
        db_name = (session.get('db') or '').strip()
        user = (session.get('user') or '').strip()

        if target_db_pattern and target_db_pattern not in db_name:
            return True
        if target_user_pattern and target_user_pattern not in user:
            return True
        return False

    @classmethod
    def _is_whitelisted(cls, rule, db_connection, session):
        user = (session.get('user') or '').strip().lower()
        host = (session.get('host') or '').strip().lower()
        db_name = (session.get('db') or '').strip().lower()
        sql_text = (session.get('sql_text') or '').strip()
        fingerprint = SqlFingerprintService.normalize(sql_text)

        if not session.get('thread_id'):
            return True

        dynamic_users = {item.lower() for item in SqlThrottleExecutorService.DEFAULT_EXCLUDE_USERS}
        if db_connection.username:
            dynamic_users.add(str(db_connection.username).strip().lower())
        if user in dynamic_users:
            return True

        for blocked in rule.to_dict().get('exclude_users', []):
            if blocked.strip().lower() == user:
                return True
        for blocked in rule.to_dict().get('exclude_hosts', []):
            if blocked.strip().lower() and blocked.strip().lower() in host:
                return True
        for blocked in rule.to_dict().get('exclude_dbs', []):
            if blocked.strip().lower() == db_name:
                return True
        for blocked in rule.to_dict().get('exclude_fingerprints', []):
            normalized_blocked = SqlFingerprintService.normalize(blocked)
            if normalized_blocked and normalized_blocked == fingerprint:
                return True
        return False

    @staticmethod
    def _group_by_fingerprint(sessions):
        grouped = defaultdict(list)
        for session in sessions:
            grouped[session['fingerprint']].append(session)
        return grouped

    @classmethod
    def _pick_candidates(cls, rule, grouped_sessions):
        rows = []
        threshold = int(rule.fingerprint_concurrency_threshold)
        slow_threshold = int(rule.slow_sql_seconds)
        for fingerprint, sessions in grouped_sessions.items():
            concurrency_count = len(sessions)
            if concurrency_count < threshold:
                continue

            exec_times = [int(item.get('exec_time_seconds') or 0) for item in sessions]
            if not any(item >= slow_threshold for item in exec_times):
                continue

            rows.append({
                'fingerprint': fingerprint,
                'fingerprint_hash': sessions[0]['fingerprint_hash'],
                'concurrency_count': concurrency_count,
                'max_exec_time': max(exec_times) if exec_times else 0,
                'avg_exec_time': round(sum(exec_times) / concurrency_count, 2) if concurrency_count else 0,
                'sum_exec_time': sum(exec_times),
                'sample_sql_text': sessions[0]['sql_text'],
                'thread_ids': [item['thread_id'] for item in sessions],
                'sessions': sorted(
                    sessions,
                    key=lambda item: (
                        -int(item.get('exec_time_seconds') or 0),
                        int(item.get('thread_id') or 0),
                    ),
                ),
            })

        rows.sort(
            key=lambda item: (
                -item['concurrency_count'],
                -item['max_exec_time'],
                -item['sum_exec_time'],
                item['fingerprint'],
            )
        )
        return rows

    @classmethod
    def _update_fingerprint_states(cls, rule, candidates):
        now = datetime.now()
        hashes = {item['fingerprint_hash'] for item in candidates}
        existing_rows = SqlThrottleFingerprintState.query.filter(
            SqlThrottleFingerprintState.rule_id == rule.id
        ).all()
        by_hash = {row.fingerprint_hash: row for row in existing_rows}

        for fingerprint_hash, row in by_hash.items():
            if fingerprint_hash in hashes:
                continue
            row.consecutive_hit_count = 0
            row.last_seen_at = now

        for candidate in candidates:
            row = by_hash.get(candidate['fingerprint_hash'])
            if not row:
                row = SqlThrottleFingerprintState(
                    rule_id=rule.id,
                    fingerprint_hash=candidate['fingerprint_hash'],
                    fingerprint=candidate['fingerprint'],
                    consecutive_hit_count=0,
                )
                db.session.add(row)
                by_hash[candidate['fingerprint_hash']] = row
            row.fingerprint = candidate['fingerprint']
            row.consecutive_hit_count = int(row.consecutive_hit_count or 0) + 1
            row.last_seen_at = now
            row.last_hit_at = now

        db.session.flush()
        return {hash_key: int(item.consecutive_hit_count or 0) for hash_key, item in by_hash.items()}

    @classmethod
    def _handle_hits(cls, rule, run, db_connection, hit_groups, trigger_source):
        kill_attempt_count = 0
        kill_success_count = 0
        logs = []
        remaining = int(rule.max_kill_per_round)

        for group in hit_groups:
            if remaining <= 0:
                break

            selected_sessions = group['sessions'][:remaining]
            for session in selected_sessions:
                kill_attempt_count += 1
                remaining -= 1
                kill_result, kill_error = cls._kill_one(rule, db_connection, session)
                if kill_result == 'success':
                    kill_success_count += 1

                kill_log = SqlThrottleKillLog(
                    run_id=run.id,
                    rule_id=rule.id,
                    thread_id=int(session['thread_id']),
                    db_user=session.get('user'),
                    db_host=session.get('host'),
                    db_name=session.get('db'),
                    fingerprint=session.get('fingerprint'),
                    sample_sql_text=session.get('sql_text'),
                    exec_time_seconds=int(session.get('exec_time_seconds') or 0),
                    kill_command=rule.kill_command,
                    kill_result=kill_result,
                    kill_error_message=kill_error,
                    killed_at=datetime.now(),
                )
                db.session.add(kill_log)
                logs.append({
                    'thread_id': kill_log.thread_id,
                    'db_user': kill_log.db_user,
                    'db_name': kill_log.db_name,
                    'kill_result': kill_log.kill_result,
                    'kill_error_message': kill_log.kill_error_message,
                    'trigger_source': trigger_source,
                })
                if remaining <= 0:
                    break
        db.session.flush()
        return kill_attempt_count, kill_success_count, logs

    @classmethod
    def _kill_one(cls, rule, db_connection, session):
        if rule.dry_run:
            return 'dry_run', None

        thread_id = int(session.get('thread_id') or 0)
        if thread_id <= 0:
            return 'failed', 'thread_id 无效'

        conn = None
        try:
            conn = pymysql.connect(
                host=db_connection.host,
                port=int(db_connection.port),
                user=db_connection.username,
                password=db_connection.password,
                connect_timeout=5,
                read_timeout=10,
                write_timeout=10,
                charset='utf8mb4',
                autocommit=True,
            )
            with conn.cursor() as cursor:
                cursor.execute(f'KILL QUERY {thread_id}')
            return 'success', None
        except pymysql.MySQLError as exc:
            category = cls._classify_mysql_error(exc)
            return category, str(exc)
        except Exception as exc:
            return 'failed', str(exc)
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _classify_mysql_error(exc):
        message = str(exc).lower()
        code = getattr(exc, 'args', [None])[0]
        if code in (1094,) or 'unknown thread id' in message or 'no such thread' in message:
            return 'thread_not_found'
        if code in (1044, 1045, 1227) or 'denied' in message or 'not owner of thread' in message:
            return 'permission_denied'
        if 'already' in message and 'gone' in message:
            return 'already_finished'
        return 'failed'
