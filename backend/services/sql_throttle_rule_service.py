from datetime import datetime

from extensions import db
from models import DbConnection
from models.sql_throttle_rule import SqlThrottleRule
from services.sql_throttle_executor_service import SqlThrottleExecutorService


class SqlThrottleRuleService:
    DEFAULTS = {
        'slow_sql_seconds': 10,
        'fingerprint_concurrency_threshold': 20,
        'poll_interval_seconds': 15,
        'max_kill_per_round': 10,
        'dry_run': True,
        'consecutive_hit_times': 2,
        'kill_command': 'KILL QUERY',
        'kill_scope': 'same_fingerprint_only',
        'kill_order': 'dup_count_desc_exec_time_desc',
    }

    @classmethod
    def list_rules(cls, page=1, per_page=10, rule_name='', enabled=None, db_connection_id=None):
        query = SqlThrottleRule.query
        if rule_name:
            query = query.filter(SqlThrottleRule.rule_name.like(f'%{rule_name}%'))
        if enabled is not None:
            query = query.filter(SqlThrottleRule.enabled == (1 if enabled else 0))
        if db_connection_id:
            query = query.filter(SqlThrottleRule.db_connection_id == db_connection_id)

        total = query.count()
        rows = query.order_by(SqlThrottleRule.updated_at.desc(), SqlThrottleRule.id.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
        return {
            'items': [item.to_dict() for item in rows.items],
            'total': total,
            'page': page,
            'per_page': per_page,
        }

    @staticmethod
    def get_rule_detail(rule_id):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None
        return rule.to_dict()

    @classmethod
    def create_rule(cls, payload, current_user):
        valid, message = cls.validate_payload(payload)
        if not valid:
            return None, message

        db_connection = db.session.get(DbConnection, int(payload['db_connection_id']))
        if not db_connection or db_connection.is_enabled == 0:
            return None, '数据库连接不存在或已禁用'

        existing = SqlThrottleRule.query.filter(SqlThrottleRule.rule_name == payload['rule_name']).first()
        if existing:
            return None, '规则名称已存在'

        try:
            rule = SqlThrottleRule(
                rule_name=payload['rule_name'].strip(),
                db_connection_id=db_connection.id,
                connection_name=db_connection.connection_name,
                enabled=1 if payload.get('enabled') else 0,
                slow_sql_seconds=int(payload.get('slow_sql_seconds', cls.DEFAULTS['slow_sql_seconds'])),
                fingerprint_concurrency_threshold=int(
                    payload.get('fingerprint_concurrency_threshold', cls.DEFAULTS['fingerprint_concurrency_threshold'])
                ),
                poll_interval_seconds=int(payload.get('poll_interval_seconds', cls.DEFAULTS['poll_interval_seconds'])),
                max_kill_per_round=int(payload.get('max_kill_per_round', cls.DEFAULTS['max_kill_per_round'])),
                min_rows_examined=payload.get('min_rows_examined'),
                target_db_pattern=(payload.get('target_db_pattern') or '').strip() or None,
                target_user_pattern=(payload.get('target_user_pattern') or '').strip() or None,
                dry_run=1 if payload.get('dry_run', cls.DEFAULTS['dry_run']) else 0,
                kill_command=cls.DEFAULTS['kill_command'],
                kill_scope=cls.DEFAULTS['kill_scope'],
                kill_order=cls.DEFAULTS['kill_order'],
                consecutive_hit_times=int(payload.get('consecutive_hit_times', cls.DEFAULTS['consecutive_hit_times'])),
                status='idle',
                creator_user_id=current_user.id if current_user else None,
            )
            rule.set_exclude_users(payload.get('exclude_users', []))
            rule.set_exclude_hosts(payload.get('exclude_hosts', []))
            rule.set_exclude_dbs(payload.get('exclude_dbs', []))
            rule.set_exclude_fingerprints(payload.get('exclude_fingerprints', []))

            db.session.add(rule)
            db.session.commit()
            return rule.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            return None, str(exc)

    @classmethod
    def update_rule(cls, rule_id, payload):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None, '规则不存在'

        merged = {
            'rule_name': payload.get('rule_name', rule.rule_name),
            'db_connection_id': payload.get('db_connection_id', rule.db_connection_id),
            'slow_sql_seconds': payload.get('slow_sql_seconds', rule.slow_sql_seconds),
            'fingerprint_concurrency_threshold': payload.get(
                'fingerprint_concurrency_threshold',
                rule.fingerprint_concurrency_threshold,
            ),
            'poll_interval_seconds': payload.get('poll_interval_seconds', rule.poll_interval_seconds),
            'max_kill_per_round': payload.get('max_kill_per_round', rule.max_kill_per_round),
            'consecutive_hit_times': payload.get('consecutive_hit_times', rule.consecutive_hit_times),
        }
        valid, message = cls.validate_payload(merged)
        if not valid:
            return None, message

        db_connection = db.session.get(DbConnection, int(merged['db_connection_id']))
        if not db_connection or db_connection.is_enabled == 0:
            return None, '数据库连接不存在或已禁用'

        duplicate = SqlThrottleRule.query.filter(
            SqlThrottleRule.rule_name == merged['rule_name'].strip(),
            SqlThrottleRule.id != rule_id,
        ).first()
        if duplicate:
            return None, '规则名称已存在'

        try:
            rule.rule_name = merged['rule_name'].strip()
            rule.db_connection_id = db_connection.id
            rule.connection_name = db_connection.connection_name
            rule.enabled = 1 if payload.get('enabled', bool(rule.enabled)) else 0
            rule.slow_sql_seconds = int(merged['slow_sql_seconds'])
            rule.fingerprint_concurrency_threshold = int(merged['fingerprint_concurrency_threshold'])
            rule.poll_interval_seconds = int(merged['poll_interval_seconds'])
            rule.max_kill_per_round = int(merged['max_kill_per_round'])
            rule.min_rows_examined = payload.get('min_rows_examined', rule.min_rows_examined)
            rule.target_db_pattern = payload.get('target_db_pattern', rule.target_db_pattern) or None
            rule.target_user_pattern = payload.get('target_user_pattern', rule.target_user_pattern) or None
            rule.dry_run = 1 if payload.get('dry_run', bool(rule.dry_run)) else 0
            rule.consecutive_hit_times = int(merged['consecutive_hit_times'])
            if 'exclude_users' in payload:
                rule.set_exclude_users(payload.get('exclude_users'))
            if 'exclude_hosts' in payload:
                rule.set_exclude_hosts(payload.get('exclude_hosts'))
            if 'exclude_dbs' in payload:
                rule.set_exclude_dbs(payload.get('exclude_dbs'))
            if 'exclude_fingerprints' in payload:
                rule.set_exclude_fingerprints(payload.get('exclude_fingerprints'))

            db.session.commit()
            return rule.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            return None, str(exc)

    @staticmethod
    def enable_rule(rule_id):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None, '规则不存在'
        rule.enabled = 1
        rule.status = 'idle'
        db.session.commit()
        return rule.to_dict(), None

    @staticmethod
    def disable_rule(rule_id):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None, '规则不存在'
        rule.enabled = 0
        rule.status = 'disabled'
        db.session.commit()
        return rule.to_dict(), None

    @staticmethod
    def delete_rule(rule_id):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None, '规则不存在'
        rule.enabled = 0
        rule.status = 'deleted'
        rule.updated_at = datetime.now()
        db.session.commit()
        return {'id': rule_id}, None

    @staticmethod
    def run_once(rule_id):
        rule = db.session.get(SqlThrottleRule, rule_id)
        if not rule:
            return None, '规则不存在'
        run, error = SqlThrottleExecutorService.execute_rule(rule, trigger_source='manual')
        if error:
            return None, error
        return run.to_dict(), None

    @staticmethod
    def validate_payload(payload):
        rule_name = (payload.get('rule_name') or '').strip()
        if not rule_name:
            return False, 'rule_name 是必填字段'

        try:
            db_connection_id = int(payload.get('db_connection_id'))
        except (TypeError, ValueError):
            return False, 'db_connection_id 必须为整数'
        if db_connection_id <= 0:
            return False, 'db_connection_id 必须大于 0'

        validators = [
            ('slow_sql_seconds', 1, 'slow_sql_seconds 必须大于 0'),
            ('fingerprint_concurrency_threshold', 2, 'fingerprint_concurrency_threshold 必须大于 1'),
            ('poll_interval_seconds', 5, 'poll_interval_seconds 必须大于等于 5'),
            ('max_kill_per_round', 1, 'max_kill_per_round 必须大于 0'),
            ('consecutive_hit_times', 1, 'consecutive_hit_times 必须大于等于 1'),
        ]
        for field, min_value, error_message in validators:
            try:
                value = int(payload.get(field))
            except (TypeError, ValueError):
                return False, f'{field} 必须为整数'
            if value < min_value:
                return False, error_message

        return True, None
