#!/usr/bin/env python3
import sys
sys.path.insert(0, '/data/claude-project/backend')

from extensions import db
from app import app

with app.app_context():
    from models import ExecutionLog
    logs = ExecutionLog.query.order_by(ExecutionLog.created_at.desc()).limit(5).all()
    print(f"Found {len(logs)} logs:")
    for log in logs:
        print(f"ID: {log.id}, Task ID: {log.task_id}, Status: {log.status}")
        print(f"  Start: {log.start_time}")
        print(f"  End: {log.end_time}")
        print(f"  Log file: {log.log_file}")
        print(f"  Error: {log.error_message}")
        print()
