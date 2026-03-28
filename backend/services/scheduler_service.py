from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
from models import CronJob, ArchiveTask
from services.pt_archiver import PTArchiver
from services.execution_log_service import ExecutionLogService
from extensions import db
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    定时任务调度器服务
    """
    _scheduler = None
    _initialized = False

    @classmethod
    def get_scheduler(cls):
        """
        获取调度器单例
        """
        if cls._scheduler is None:
            # 配置调度器，增加 misfire_grace_time
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': ThreadPoolExecutor(10),
            }
            job_defaults = {
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 同一任务只允许一个实例运行
                'misfire_grace_time': 3600  # 允许1小时的错过时间
            }
            cls._scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )
        return cls._scheduler

    @classmethod
    def initialize(cls):
        """
        初始化调度器，从数据库加载所有激活的定时任务
        """
        if cls._initialized:
            return

        scheduler = cls.get_scheduler()

        try:
            # 从数据库加载所有激活的定时任务
            active_jobs = CronJob.query.filter(CronJob.is_active == 1).all()

            for job in active_jobs:
                cls._add_job_to_scheduler(job)

            scheduler.start()
            cls._initialized = True
            logger.info(f"Scheduler initialized with {len(active_jobs)} active jobs")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")

    @classmethod
    def shutdown(cls):
        """
        关闭调度器
        """
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown()
            cls._initialized = False
            logger.info("Scheduler shutdown")

    @classmethod
    def _add_job_to_scheduler(cls, cron_job):
        """
        将定时任务添加到调度器
        """
        scheduler = cls.get_scheduler()
        job_id = f"cron_{cron_job.id}"

        # 解析 cron 表达式
        try:
            cron_parts = cron_job.cron_expression.split()
            if len(cron_parts) != 6:
                logger.error(f"Invalid cron expression: {cron_job.cron_expression}")
                return

            # APScheduler 的 CronTrigger 顺序: second, minute, hour, day, month, day_of_week
            trigger = CronTrigger(
                second=cron_parts[0],
                minute=cron_parts[1],
                hour=cron_parts[2],
                day=cron_parts[3],
                month=cron_parts[4],
                day_of_week=cron_parts[5],
                timezone='Asia/Shanghai'  # 设置时区为东八区
            )

            scheduler.add_job(
                func=cls._execute_archive_task,
                trigger=trigger,
                id=job_id,
                args=[cron_job.id],
                replace_existing=True
            )

            logger.info(f"Added cron job {job_id} with expression: {cron_job.cron_expression}")
        except Exception as e:
            logger.error(f"Failed to add cron job {cron_job.id}: {e}")

    @classmethod
    def _remove_job_from_scheduler(cls, cron_job_id):
        """
        从调度器中移除定时任务
        """
        scheduler = cls.get_scheduler()
        job_id = f"cron_{cron_job_id}"

        try:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info(f"Removed cron job {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove cron job {job_id}: {e}")

    @classmethod
    def add_job(cls, cron_job_id):
        """
        添加定时任务（在创建 CronJob 后调用）
        """
        cron_job = CronJob.query.get(cron_job_id)
        if not cron_job:
            logger.error(f"CronJob {cron_job_id} not found")
            return

        if cron_job.is_active:
            cls._add_job_to_scheduler(cron_job)

    @classmethod
    def update_job(cls, cron_job_id):
        """
        更新定时任务（在更新 CronJob 后调用）
        """
        cron_job = CronJob.query.get(cron_job_id)
        if not cron_job:
            logger.error(f"CronJob {cron_job_id} not found")
            return

        # 先移除旧的任务
        cls._remove_job_from_scheduler(cron_job_id)

        # 如果激活，则添加新任务
        if cron_job.is_active:
            cls._add_job_to_scheduler(cron_job)

    @classmethod
    def delete_job(cls, cron_job_id):
        """
        删除定时任务（在删除 CronJob 后调用）
        """
        cls._remove_job_from_scheduler(cron_job_id)

    @classmethod
    def toggle_job(cls, cron_job_id):
        """
        切换定时任务状态
        """
        cron_job = CronJob.query.get(cron_job_id)
        if not cron_job:
            logger.error(f"CronJob {cron_job_id} not found")
            return

        if cron_job.is_active:
            cls._add_job_to_scheduler(cron_job)
        else:
            cls._remove_job_from_scheduler(cron_job_id)

    @staticmethod
    def _execute_archive_task(cron_job_id):
        """
        执行归档任务（由调度器调用）
        """
        # 直接导入应用实例来创建上下文，避免 current_app 依赖
        from app import app
        with app.app_context():
            try:
                cron_job = CronJob.query.get(cron_job_id)
                if not cron_job or not cron_job.is_active:
                    logger.warning(f"CronJob {cron_job_id} is inactive or not found, skipping")
                    return

                task = ArchiveTask.query.get(cron_job.task_id)
                if not task or task.is_enabled == 0:
                    logger.warning(f"ArchiveTask {cron_job.task_id} is disabled or not found, skipping")
                    return

                logger.info(f"Executing scheduled archive task: {task.task_name} (cron job: {cron_job_id})")

                # 创建执行日志，状态为执行中
                start_time = datetime.now()
                log_data = {
                    'task_id': task.id,
                    'cron_job_id': cron_job_id,
                    'start_time': start_time,
                    'status': 2  # 执行中
                }
                log, log_error = ExecutionLogService.create_log(log_data)
                if log_error:
                    logger.error(f"Failed to create execution log: {log_error}")
                    return

                # 执行归档
                try:
                    success, log_file, error_msg = PTArchiver.execute_archive(task)

                    # 更新日志
                    update_data = {
                        'end_time': datetime.now(),
                        'status': 1 if success else 0,
                        'log_file': log_file,
                        'error_message': error_msg
                    }
                    ExecutionLogService.update_log(log['id'], update_data)

                    # 更新定时任务的运行时间信息
                    cron_job.last_run_time = datetime.now()

                    # 计算下次运行时间
                    try:
                        cron_parts = cron_job.cron_expression.split()
                        if len(cron_parts) == 6:
                            next_trigger = CronTrigger(
                                second=cron_parts[0],
                                minute=cron_parts[1],
                                hour=cron_parts[2],
                                day=cron_parts[3],
                                month=cron_parts[4],
                                day_of_week=cron_parts[5],
                                timezone='Asia/Shanghai'
                            )
                            cron_job.next_run_time = next_trigger.get_next_fire_time(datetime.now(), datetime.now())
                    except Exception as e:
                        logger.warning(f"Failed to calculate next run time for cron job {cron_job.id}: {e}")

                    db.session.commit()

                    if success:
                        logger.info(f"Scheduled archive task completed successfully: {task.task_name}")
                    else:
                        logger.error(f"Scheduled archive task failed: {task.task_name}, error: {error_msg}")
                except Exception as e:
                    # 更新日志为失败
                    update_data = {
                        'end_time': datetime.now(),
                        'status': 0,
                        'error_message': str(e)
                    }
                    ExecutionLogService.update_log(log['id'], update_data)
                    logger.error(f"Exception during scheduled archive task: {e}")

            except Exception as e:
                logger.error(f"Exception in _execute_archive_task: {e}")
