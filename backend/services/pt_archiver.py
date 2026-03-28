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
        # 提取所有需要的数据，避免在后台线程中访问关系属性
        source_conn = {
            'host': task.source_connection.host,
            'port': task.source_connection.port,
            'username': task.source_connection.username,
            'password': task.source_connection.password
        }
        dest_conn = None
        if task.dest_connection:
            dest_conn = {
                'host': task.dest_connection.host,
                'port': task.dest_connection.port,
                'username': task.dest_connection.username,
                'password': task.dest_connection.password
            }

        # 保存任务属性副本
        task_data = {
            'source_table': task.source_table,
            'source_database': task.source_database,
            'dest_database': task.dest_database,
            'dest_table': task.dest_table,
            'where_condition': task.where_condition
        }

        def _run():
            from app import app  # 延迟导入应用实例
            from extensions import db
            from models import ExecutionLog

            log_file = cls.generate_log_file_path(
                task_data['source_table'],
                source_conn['host']
            )

            source_str = cls.build_source_str(
                type('', (), source_conn)(),  # 简单的模拟对象
                task_data['source_database'],
                task_data['source_table']
            )

            dest_str = None
            if dest_conn:
                dest_str = cls.build_dest_str(
                    type('', (), dest_conn)(),  # 简单的模拟对象
                    task_data['dest_database'],
                    task_data['dest_table']
                )

            command = cls.build_archive_command(
                source_str,
                dest_str,
                task_data['where_condition'],
                log_file
            )

            print(f"Executing async command: {command}")

            # 使用 Popen 异步执行，不阻塞
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 等待进程完成，超时1小时
            try:
                exit_code = process.wait(timeout=3600)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = -1

            # 更新日志，需要应用上下文
            with app.app_context():
                log = ExecutionLog.query.get(log_id)
                if log:
                    end_time = datetime.datetime.now()
                    if exit_code == 0:
                        log.end_time = end_time
                        log.status = 1
                        log.log_file = log_file
                        log.error_message = None
                    else:
                        # 尝试从日志文件读取错误信息
                        error_msg = None
                        try:
                            if os.path.exists(log_file):
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    error_msg = f.read().strip()
                        except:
                            pass
                        if not error_msg:
                            error_msg = f"pt-archiver execution failed (exit code: {exit_code})"

                        log.end_time = end_time
                        log.status = 0
                        log.log_file = log_file if os.path.exists(log_file) else None
                        log.error_message = error_msg

                    db.session.commit()
                    print(f"Log {log_id} updated successfully")
                else:
                    print(f"Log {log_id} not found")

        # 在后台线程中运行
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
