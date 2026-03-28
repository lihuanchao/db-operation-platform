#!/usr/bin/env python3
import sys
sys.path.insert(0, '/data/claude-project/backend')

from extensions import db
from app import app
from models import ArchiveTask, ExecutionLog
from services.pt_archiver import PTArchiver
from services.execution_log_service import ExecutionLogService
import time

with app.app_context():
    # 获取一个任务
    task = ArchiveTask.query.get(1)
    if not task:
        print("No task found")
        sys.exit(1)

    print(f"Found task: {task.task_name}")
    print(f"Source connection: {task.source_connection}")

    # 创建执行日志
    from datetime import datetime
    log_data = {
        'task_id': task.id,
        'start_time': datetime.now(),
        'status': 2
    }
    log, log_error = ExecutionLogService.create_log(log_data)
    if log_error:
        print(f"Log error: {log_error}")
        sys.exit(1)

    print(f"Created log ID: {log['id']}")

    # 测试回调函数
    def test_callback(log_id, data):
        print(f"Callback called for log {log_id}")
        print(f"Data: {data}")
        with app.app_context():
            ExecutionLogService.update_log(log_id, data)
            print("Log updated successfully!")

    # 启动异步执行
    print("Starting async execution...")
    PTArchiver.execute_archive_async(task, log['id'], test_callback)

    # 等待一段时间
    print("Waiting for 10 seconds...")
    time.sleep(10)

    # 检查日志
    updated_log = ExecutionLog.query.get(log['id'])
    print(f"\nFinal log status: {updated_log.status}")
    print(f"End time: {updated_log.end_time}")
    print(f"Log file: {updated_log.log_file}")
    print(f"Error: {updated_log.error_message}")
