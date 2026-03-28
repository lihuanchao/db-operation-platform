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

    # 启动异步执行
    print("Starting async execution...")
    PTArchiver.execute_archive_async(task, log['id'])

    # 等待一段时间
    print("Waiting for 15 seconds...")
    for i in range(15):
        time.sleep(1)
        if i % 5 == 0:
            print(f"Waiting... {i}s")

    # 检查日志 - 需要重新创建会话以看到最新数据
    db.session.remove()  # 关闭当前会话
    updated_log = ExecutionLog.query.get(log['id'])
    print(f"\nFinal log status: {updated_log.status}")
    print(f"End time: {updated_log.end_time}")
    print(f"Log file: {updated_log.log_file}")
    print(f"Error: {updated_log.error_message}")

    if updated_log.log_file:
        import os
        if os.path.exists(updated_log.log_file):
            print(f"\nLog file exists. Reading content...")
            with open(updated_log.log_file, 'r', encoding='utf-8') as f:
                print(f.read())
