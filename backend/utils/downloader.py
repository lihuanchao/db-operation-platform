from datetime import datetime


class Downloader:
    @staticmethod
    def generate_markdown(slow_sqls):
        """
        生成Markdown格式的优化建议文档
        """
        markdown = f"# 慢SQL优化建议报告\n\n"
        markdown += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown += f"---\n\n"

        for idx, slow_sql in enumerate(slow_sqls, 1):
            markdown += f"## {idx}. 慢SQL信息\n\n"
            if hasattr(slow_sql, 'checksum'):
                markdown += f"- **Checksum**: {slow_sql.checksum}\n"
            markdown += f"- **数据库**: {slow_sql.database_name}\n"
            if hasattr(slow_sql, 'system_name'):
                markdown += f"- **系统**: {slow_sql.system_name}\n"
            exec_time = getattr(slow_sql, 'execution_time', None)
            if exec_time is None:
                exec_time = getattr(slow_sql, 'avg_time', 'N/A')
            markdown += f"- **执行时间**: {exec_time}秒\n"
            markdown += f"- **执行次数**: {slow_sql.execution_count}\n"
            created_at = getattr(slow_sql, 'created_at', None)
            if created_at is None:
                created_at = getattr(slow_sql, 'last_seen', None)
            if created_at:
                if hasattr(created_at, 'strftime'):
                    markdown += f"- **采集时间**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                else:
                    markdown += f"- **采集时间**: {created_at}\n\n"

            markdown += f"### SQL语句\n\n"
            sql_text = getattr(slow_sql, 'sql_text', None)
            if sql_text is None:
                sql_text = getattr(slow_sql, 'sample', '')
            markdown += f"```sql\n{sql_text}\n```\n\n"

            markdown += f"### 优化建议\n\n"
            if slow_sql.optimized_suggestion:
                markdown += f"{slow_sql.optimized_suggestion}\n\n"
            else:
                markdown += f"*暂未获取优化建议*\n\n"

            markdown += f"---\n\n"

        return markdown

    @staticmethod
    def generate_csv(slow_sqls):
        """
        生成CSV格式的慢SQL数据
        """
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # 写入表头
        writer.writerow(['主机', '数据库', 'SQL语句', '次数', '平均时间', '最近出现', '优化建议'])

        for slow_sql in slow_sqls:
            # 提取字段
            host = getattr(slow_sql, 'host', 'N/A')
            database = getattr(slow_sql, 'database_name', 'N/A')
            sql_text = getattr(slow_sql, 'sql_text', getattr(slow_sql, 'sample', ''))
            execution_count = getattr(slow_sql, 'execution_count', 0)
            avg_time = getattr(slow_sql, 'avg_time', 'N/A')
            if avg_time and not isinstance(avg_time, str):
                avg_time = f"{avg_time:.2f}"

            last_seen = getattr(slow_sql, 'last_seen', 'N/A')
            if last_seen and hasattr(last_seen, 'strftime'):
                last_seen = last_seen.strftime('%Y-%m-%d %H:%M:%S')

            optimized_suggestion = getattr(slow_sql, 'optimized_suggestion', '暂未获取优化建议')

            writer.writerow([
                host,
                database,
                sql_text,
                execution_count,
                avg_time,
                last_seen,
                optimized_suggestion
            ])

        return output.getvalue()
