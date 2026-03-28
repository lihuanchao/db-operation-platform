from datetime import datetime
from models import CronJob, ArchiveTask
from extensions import db
from services.scheduler_service import SchedulerService


class CronService:
    """
    定时任务服务
    """

    @staticmethod
    def get_job_list(page=1, per_page=10, task_id=None):
        """
        获取定时任务列表
        """
        query = CronJob.query

        if task_id:
            query = query.filter(CronJob.task_id == task_id)

        total = query.count()
        jobs = query.order_by(CronJob.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': [job.to_dict() for job in jobs.items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def get_job_detail(job_id):
        """
        获取定时任务详情
        """
        job = CronJob.query.get(job_id)
        if not job:
            return None
        return job.to_dict()

    @staticmethod
    def create_job(data):
        """
        创建定时任务
        """
        try:
            # 验证归档任务存在
            task = ArchiveTask.query.get(data['task_id'])
            if not task or task.is_enabled == 0:
                return None, '归档任务不存在或已禁用'

            # 计算下次运行时间
            next_run_time = data.get('next_run_time')
            if not next_run_time:
                try:
                    from apscheduler.triggers.cron import CronTrigger
                    cron_parts = data['cron_expression'].split()
                    if len(cron_parts) == 6:
                        trigger = CronTrigger(
                            second=cron_parts[0],
                            minute=cron_parts[1],
                            hour=cron_parts[2],
                            day=cron_parts[3],
                            month=cron_parts[4],
                            day_of_week=cron_parts[5],
                            timezone='Asia/Shanghai'
                        )
                        next_run_time = trigger.get_next_fire_time(datetime.now(), datetime.now())
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to calculate next run time: {e}")

            job = CronJob(
                task_id=data['task_id'],
                cron_expression=data['cron_expression'],
                next_run_time=next_run_time,
                is_active=data.get('is_active', 1)
            )

            db.session.add(job)
            db.session.commit()

            # 添加到调度器
            SchedulerService.add_job(job.id)

            return job.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_job(job_id, data):
        """
        更新定时任务
        """
        try:
            job = CronJob.query.get(job_id)
            if not job:
                return None, '定时任务不存在'

            if 'cron_expression' in data:
                job.cron_expression = data['cron_expression']
                # 重新计算下次运行时间
                try:
                    from apscheduler.triggers.cron import CronTrigger
                    cron_parts = job.cron_expression.split()
                    if len(cron_parts) == 6:
                        trigger = CronTrigger(
                            second=cron_parts[0],
                            minute=cron_parts[1],
                            hour=cron_parts[2],
                            day=cron_parts[3],
                            month=cron_parts[4],
                            day_of_week=cron_parts[5],
                            timezone='Asia/Shanghai'
                        )
                        job.next_run_time = trigger.get_next_fire_time(datetime.now(), datetime.now())
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to calculate next run time for cron job {job.id}: {e}")

            if 'next_run_time' in data and 'cron_expression' not in data:
                job.next_run_time = data['next_run_time']

            if 'is_active' in data:
                job.is_active = 1 if data['is_active'] else 0

            db.session.commit()

            # 更新调度器
            SchedulerService.update_job(job.id)

            return job.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def toggle_job(job_id):
        """
        切换定时任务状态
        """
        try:
            job = CronJob.query.get(job_id)
            if not job:
                return None, '定时任务不存在'

            job.is_active = 0 if job.is_active else 1
            db.session.commit()

            # 更新调度器
            SchedulerService.toggle_job(job.id)

            return job.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_job(job_id):
        """
        删除定时任务
        """
        try:
            job = CronJob.query.get(job_id)
            if not job:
                return None, '定时任务不存在'

            # 从调度器中移除
            SchedulerService.delete_job(job.id)

            db.session.delete(job)
            db.session.commit()

            return {'id': job_id}, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
