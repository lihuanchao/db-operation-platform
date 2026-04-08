import glob
import os


class FlashbackService:
    TOOL_PATH = '/my2sql'
    OUTPUT_ROOT = '/app/flashback/tasks'

    @classmethod
    def build_command(cls, task, connection, output_dir):
        command = [
            cls.TOOL_PATH,
            '-databases', task.database_name,
            '-tables', task.table_name,
            '-mode', task.mode or 'repl',
            '-host', connection.host,
            '-port', str(connection.port),
            '-user', connection.username,
            '-password', connection.password,
            '-sql', task.sql_type,
        ]

        optional_pairs = [
            ('-start-datetime', task.start_datetime),
            ('-stop-datetime', task.stop_datetime),
            ('-start-file', task.start_file),
            ('-stop-file', task.stop_file),
        ]
        for flag, value in optional_pairs:
            if value:
                command.extend([flag, value])

        command.extend([
            '-work-type', task.work_type,
            '-output-dir', output_dir,
        ])
        return command, cls.mask_command(command)

    @staticmethod
    def mask_command(command):
        masked = list(command)
        for index, part in enumerate(masked):
            if part == '-password' and index + 1 < len(masked):
                masked[index + 1] = '******'
        return ' '.join(masked)

    @staticmethod
    def collect_artifacts(output_dir):
        items = []
        for name in ('binlog_status.txt', 'biglong_trx.txt'):
            path = os.path.join(output_dir, name)
            if not os.path.exists(path):
                raise FileNotFoundError(name)
            items.append({
                'name': name,
                'path': path,
                'size': os.path.getsize(path),
            })

        sql_files = sorted(glob.glob(os.path.join(output_dir, '*.sql')), key=os.path.basename)
        if not sql_files:
            raise FileNotFoundError('*.sql')
        sql_path = sql_files[0]
        items.append({
            'name': os.path.basename(sql_path),
            'path': sql_path,
            'size': os.path.getsize(sql_path),
        })
        return items

