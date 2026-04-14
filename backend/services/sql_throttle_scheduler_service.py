import logging
from datetime import datetime, timedelta

from models.sql_throttle_rule import SqlThrottleRule
from models.sql_throttle_run import SqlThrottleRun
from services.sql_throttle_executor_service import SqlThrottleExecutorService

logger = logging.getLogger(__name__)


class SqlThrottleSchedulerService:
    JOB_ID = 'sql_throttle_rule_scanner'
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        from services.scheduler_service import SchedulerService

        scheduler = SchedulerService.get_scheduler()
        if scheduler.get_job(cls.JOB_ID):
            cls._initialized = True
            return

        scheduler.add_job(
            func=cls._scan_rules,
            trigger='interval',
            seconds=5,
            id=cls.JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        cls._initialized = True
        logger.info('SQL throttle scheduler initialized')

    @staticmethod
    def _scan_rules():
        from app import app
        from extensions import db

        try:
            with app.app_context():
                rules = SqlThrottleRule.query.filter(SqlThrottleRule.enabled == 1).all()
                now = datetime.now()
                for rule in rules:
                    if rule.status == 'running':
                        continue
                    if rule.last_run_at and now - rule.last_run_at < timedelta(seconds=max(rule.poll_interval_seconds, 5)):
                        continue

                    running = SqlThrottleRun.query.filter(
                        SqlThrottleRun.rule_id == rule.id,
                        SqlThrottleRun.status == 'running',
                    ).first()
                    if running:
                        skipped = SqlThrottleRun(
                            rule_id=rule.id,
                            status='skipped',
                            dry_run=1 if rule.dry_run else 0,
                            sample_started_at=now,
                            sample_finished_at=now,
                            error_message='上一轮尚未结束，跳过本轮执行',
                        )
                        db.session.add(skipped)
                        db.session.commit()
                        continue

                    _, error = SqlThrottleExecutorService.execute_rule(rule, trigger_source='scheduler')
                    if error:
                        logger.error('SQL throttle run failed for rule %s: %s', rule.id, error)
        except Exception as exc:
            logger.error('SQL throttle scheduler scan failed: %s', exc)
