import subprocess
import os
import datetime
import uuid
import threading
import time


class PTArchiver:
    """
    pt-archiver 工具执行服务
    """

    DEFAULT_ARGS = {
        'charset': 'utf8mb4',
        'limit': '10000',
        'txn_size': '10000',
        'progress': '50000',
        'statistics': True,
        'bulk_insert': True
    }

    @staticmethod
    def build_source_str(connection, database, table):
        """
        构建源库字符串
        :param connection: DbConnection 对象
        :param database: 数据库名
        :param table: 表名
        :return: 源库字符串
        """
        return (
            f"h={connection.host},P={connection.port},u={connection.username},"
            f"D={database},t={table},b=true,p={connection.password}"
        )

    @staticmethod
    def build_dest_str(connection, database, table):
        """
        构建目标库字符串
        :param connection: DbConnection 对象
        :param database: 数据库名
        :param table: 表名
        :return: 目标库字符串
        """
        if not connection or not database or not table:
            return None
        return (
            f"h={connection.host},P={connection.port},u={connection.username},"
            f"D={database},t={table},b=true,p={connection.password}"
        )

    @staticmethod
    def generate_log_file_path(table_name, connection_host):
        """
        生成日志文件路径
        :param table_name: 表名
        :param connection_host: 连接主机地址
        :return: 日志文件路径
        """
        log_dir = '/app/arch/log'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, mode=0o755, exist_ok=True)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        host_suffix = connection_host.replace('.', '_')
        filename = f"{table_name}_{host_suffix}_{timestamp}.log"
        return os.path.join(log_dir, filename)

    @classmethod
    def build_archive_command(cls, source_str, dest_str, where, log_file):
        """
        构建归档命令
        :param source_str: 源库字符串
        :param dest_str: 目标库字符串
        :param where: 归档条件
        :param log_file: 日志文件路径
        :return: 完整的命令字符串
        """
        cmd = ['pt-archiver', '--source', source_str]

        if dest_str:
            cmd.extend(['--dest', dest_str])
        else:
            cmd.append('--purge')

        cmd.extend(['--charset', cls.DEFAULT_ARGS['charset']])
        cmd.extend(['--where', where])
        cmd.extend(['--limit', cls.DEFAULT_ARGS['limit']])
        cmd.extend(['--txn-size', cls.DEFAULT_ARGS['txn_size']])
        cmd.extend(['--progress', cls.DEFAULT_ARGS['progress']])

        if cls.DEFAULT_ARGS['statistics']:
            cmd.append('--statistics')

        # 只有当有目标库配置时才添加 --bulk-insert 参数
        # if dest_str and cls.DEFAULT_ARGS['bulk_insert']:
        #     cmd.append('--bulk-insert')

        cmd.append(f">> {log_file} 2>&1")

        return ' '.join(cmd)

    @classmethod
    def run_command(cls, command):
        """
        执行命令
        :param command: 命令字符串
        :return: (exit_code, output, error)
        """
        try:
            # 使用 shell=True 来支持重定向等操作
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            # 如果命令有重定向，可能 stdout/stderr 都是空的，尝试从日志文件读取内容
            log_file = None
            if ">>" in command:
                log_part = command.split(">>", 1)[1].strip().split()[0]
                if log_part and log_part.startswith('"') and log_part.endswith('"'):
                    log_file = log_part[1:-1]
                elif log_part:
                    log_file = log_part

            if log_file and result.returncode != 0:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read().strip()
                        if log_content:
                            return (result.returncode, log_content, log_content)
                except:
                    pass

            return (result.returncode, result.stdout, result.stderr)
        except Exception as e:
            return (-1, '', str(e))

    @classmethod
    def execute_archive(cls, task):
        """
        执行归档任务（同步执行）
        :param task: ArchiveTask 对象
        :return: (success, log_file, error_message)
        """
        log_file = cls.generate_log_file_path(task.source_table, task.source_connection.host)

        source_str = cls.build_source_str(
            task.source_connection,
            task.source_database,
            task.source_table
        )

        dest_str = cls.build_dest_str(
            task.dest_connection,
            task.dest_database,
            task.dest_table
        )

        command = cls.build_archive_command(
            source_str,
            dest_str,
            task.where_condition,
            log_file
        )

        print(f"Executing command: {command}")

        exit_code, stdout, stderr = cls.run_command(command)

        if exit_code == 0:
            return (True, log_file, None)
        else:
            # 优先使用 run_command 方法返回的错误信息（可能是从日志文件读取的）
            error_msg = stderr or stdout
            if not error_msg:
                try:
                    # 再次尝试从日志文件读取内容
                    with open(log_file, 'r', encoding='utf-8') as f:
                        error_msg = f.read().strip() or "Command failed, but no error details available"
                except:
                    error_msg = f"pt-archiver execution failed (exit code: {exit_code})"
            return (False, log_file, error_msg)

    @classmethod
    def execute_archive_async(cls, task, log_id):
        """
        执行归档任务（异步执行，在后台线程中运行）
        :param task: ArchiveTask 对象
        :param log_id: 执行日志ID
        """
        task_id = task.id
        try:
            from flask import current_app
            flask_app = current_app._get_current_object()
        except Exception:
            from app import app as flask_app

        def _run():
            from extensions import db
            from models import ArchiveTask, ExecutionLog

            def _mark_failed(message):
                log = ExecutionLog.query.get(log_id)
                if log:
                    log.end_time = datetime.datetime.now()
                    log.status = 0
                    log.error_message = message
                    db.session.commit()
                    print(f"Log {log_id} marked as failed: {message}")

            with flask_app.app_context():
                try:
                    current_task = ArchiveTask.query.get(task_id)
                    if not current_task or current_task.is_enabled == 0:
                        _mark_failed('归档任务不存在或已禁用')
                        return

                    success, log_file, error_msg = cls.execute_archive(current_task)

                    log = ExecutionLog.query.get(log_id)
                    if not log:
                        return

                    log.end_time = datetime.datetime.now()
                    log.status = 1 if success else 0
                    log.log_file = log_file
                    log.error_message = error_msg
                    db.session.commit()
                    print(f"Log {log_id} updated successfully")
                except Exception as e:
                    db.session.rollback()
                    _mark_failed(str(e))

        # 在后台线程中运行
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
