"""
SQL 元数据服务 - 负责解析 SQL、获取表结构和执行计划
"""
import sqlparse
import pymysql
import logging
import re
from typing import List, Dict, Optional, Tuple


# 延迟导入以避免循环导入
def get_llm_service():
    from services.llm_service import LLMService
    return LLMService()


logger = logging.getLogger(__name__)


class SQLMetadataService:
    def __init__(self):
        self._llm_service = None
        self.cache = {}  # 用于缓存已经解析过的 SQL

    @property
    def llm_service(self):
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service

    def extract_table_names(self, sql_text: str) -> List[str]:
        """
        从 SQL 中提取表名 - 混合策略：简单 SQL 使用传统解析，复杂 SQL 使用 LLM
        """
        # 首先检查缓存
        sql_key = self._generate_cache_key(sql_text)
        if sql_key in self.cache:
            logger.debug(f"Using cached result for SQL: {sql_text[:50]}...")
            return self.cache[sql_key]

        # 始终使用 LLM 解析，因为它更可靠
        table_names = self._extract_tables_with_llm(sql_text)

        # 过滤和验证表名
        filtered_tables = self._filter_table_names(table_names)

        # 缓存结果
        self.cache[sql_key] = filtered_tables

        logger.debug(f"Final extracted tables: {filtered_tables}")
        return filtered_tables

    def _extract_tables_with_llm(self, sql_text: str) -> List[str]:
        """
        使用 LLM 解析 SQL 中的表名 - 主要方法
        """
        prompt = self._build_llm_prompt(sql_text)
        try:
            response = self.llm_service.get_raw_llm_response(prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}, falling back to simple parser")
            # 回退到简单解析
            return self._extract_with_simple_parser(sql_text)

    def _build_llm_prompt(self, sql_text: str) -> str:
        """
        构建 LLM 解析 SQL 表名的 prompt
        """
        return f"""请分析以下 SQL 语句，并提取其中所有引用的真实数据库表名（不包括临时表、CTE别名和子查询别名）：

SQL语句：
```{sql_text}```

要求：
1. 提取所有 FROM、JOIN、INNER JOIN、LEFT JOIN、RIGHT JOIN 等之后的表名
2. 如果是 CTE（WITH 子句），请忽略 CTE 的别名，只提取 CTE 内部 SQL 中引用的真实表名
3. 识别视图引用（视图应该被当作表名提取）
4. 绝对不要包括子查询别名和临时表
5. 输出格式：只返回逗号分隔的表名列表，不要添加任何其他内容、解释或说明

示例1：
如果 SQL 是 "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"，
返回：users, orders

示例2：
如果 SQL 是 "WITH active_users AS (SELECT * FROM users WHERE active = 1) SELECT * FROM active_users u JOIN orders o ON u.id = o.user_id"，
返回：users, orders

示例3：
如果 SQL 是 "SELECT * FROM monthly_sales_report m JOIN customers c ON m.customer_id = c.id"，
返回：monthly_sales_report, customers
"""

    def _parse_llm_response(self, response: str) -> List[str]:
        """
        解析 LLM 的响应，提取表名
        """
        try:
            # 处理各种可能的响应格式
            response = response.strip()

            # 移除可能的 markdown 代码块标记
            response = response.replace('```', '').replace('sql', '')

            # 如果是数组格式
            if '[' in response:
                import ast
                try:
                    tables = ast.literal_eval(response)
                    return [t.strip() for t in tables if t.strip()]
                except Exception:
                    pass

            # 如果是逗号分隔
            if ',' in response:
                tables = [t.strip() for t in response.split(',') if t.strip()]
                return self._filter_table_names(tables)
            elif '\n' in response:
                # 如果是换行分隔
                tables = [t.strip() for t in response.split('\n') if t.strip()]
                return self._filter_table_names(tables)
            else:
                # 如果只有一个表名
                return self._filter_table_names([response])
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return []

    def _extract_with_simple_parser(self, sql_text: str) -> List[str]:
        """
        简单解析器 - 作为 LLM 失败时的回退方案
        """
        table_names = set()

        # 使用正则表达式提取
        patterns = [
            # FROM 子句
            r'\bFROM\s+`?(\w+)`?(?:\s+`?\w+`?)?(?:\s*,\s*`?(\w+)`?)?',
            # JOIN 子句
            r'\bJOIN\s+`?(\w+)`?(?:\s+`?\w+`?)?',
            # FROM 在子查询中
            r'\bFROM\s+`?(\w+)`?'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql_text, re.IGNORECASE)
            for match in matches:
                for group in match:
                    if group and len(group) >= 2:
                        if group.lower() not in {'select', 'from', 'where', 'group', 'by', 'order', 'join', 'as', 'with'}:
                            table_names.add(group)

        return list(table_names)

    def _filter_table_names(self, table_names: List[str]) -> List[str]:
        """
        过滤掉无效的表名
        """
        filtered_tables = []
        sql_keywords = {
            'select', 'from', 'where', 'group', 'by', 'order', 'join', 'as',
            'with', 'on', 'in', 'and', 'or', 'not', 'is', 'null', 'inner',
            'left', 'right', 'outer', 'cross', 'natural', 'limit', 'offset',
            'having', 'distinct', 'all', 'union', 'except', 'intersect',
            'values', 'set', 'into', 'insert', 'update', 'delete', 'drop',
            'create', 'alter', 'table', 'database', 'schema', 'view',
            'index', 'primary', 'key', 'foreign', 'references', 'default',
            'check', 'unique', 'constraint', 'cascade', 'restrict', 'no',
            'action', 'identity', 'auto_increment', 'serial', 'bigint',
            'int', 'integer', 'smallint', 'tinyint', 'decimal', 'numeric',
            'float', 'double', 'real', 'char', 'varchar', 'text', 'blob',
            'date', 'time', 'datetime', 'timestamp', 'year', 'boolean',
            'bool', 'true', 'false', 'case', 'when', 'then', 'else', 'end'
        }

        for name in table_names:
            name = name.strip('`"\'')  # 去除引号

            # 过滤掉明显不是表名的
            if (len(name) >= 2 and
                ' ' not in name and
                ',' not in name and
                '(' not in name and
                ')' not in name and
                '[' not in name and
                ']' not in name and
                name.lower() not in sql_keywords):
                filtered_tables.append(name)

        # 去重（忽略大小写）
        seen = set()
        unique_tables = []
        for table in filtered_tables:
            if table.lower() not in seen:
                seen.add(table.lower())
                unique_tables.append(table)

        return unique_tables

    def _generate_cache_key(self, sql_text: str) -> str:
        """
        生成 SQL 缓存键（对 SQL 进行归一化处理）
        """
        # 去除多余的空格和换行
        normalized_sql = ' '.join(sql_text.strip().split())
        return normalized_sql[:200]  # 取前 200 字符作为键

    def get_connection_by_manage_host(self, db_connections, manage_host: str) -> Optional:
        """
        通过 manage_host 匹配数据库连接
        """
        if not manage_host or not db_connections:
            return None

        for conn in db_connections:
            if conn.manage_host == manage_host:
                return conn
            # 如果 manage_host 没匹配到，也尝试匹配 host
            if conn.host == manage_host:
                return conn

        return None

    def get_table_structures(self, connection_config, table_names: List[str], database_name: Optional[str] = None) -> Dict[str, str]:
        """
        获取多个表的 CREATE TABLE 语句 - 修复版：支持指定数据库
        """
        structures = {}

        if not table_names:
            return structures

        conn = None
        try:
            conn = pymysql.connect(
                host=connection_config.host,
                port=connection_config.port,
                user=connection_config.username,
                password=connection_config.password,
                database=database_name if database_name else None,
                connect_timeout=5,
                read_timeout=10
            )

            with conn.cursor() as cursor:
                for table_name in table_names:
                    try:
                        if database_name:
                            cursor.execute(f"SHOW CREATE TABLE `{database_name}`.`{table_name}`")
                        else:
                            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                        result = cursor.fetchone()
                        if result and len(result) >= 2:
                            structures[table_name] = result[1]
                    except Exception as e:
                        logger.warning(f"Failed to get structure for table {table_name}: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Failed to connect to database for table structures: {e}")
        finally:
            if conn:
                conn.close()

        return structures

    def get_execution_plan(self, connection_config, sql_text: str, database_name: Optional[str] = None) -> Optional[str]:
        """
        获取 SQL 的执行计划（JSON 格式）- 修复版：支持指定数据库
        """
        plan = None
        conn = None

        try:
            conn = pymysql.connect(
                host=connection_config.host,
                port=connection_config.port,
                user=connection_config.username,
                password=connection_config.password,
                database=database_name if database_name else None,
                connect_timeout=5,
                read_timeout=10
            )

            with conn.cursor() as cursor:
                try:
                    cursor.execute(f"EXPLAIN FORMAT=JSON {sql_text}")
                    result = cursor.fetchone()
                    if result:
                        plan = result[0]
                except Exception as e:
                    logger.warning(f"Failed to get execution plan: {e}")
                    # 如果 FORMAT=JSON 失败，尝试普通 EXPLAIN
                    try:
                        cursor.execute(f"EXPLAIN {sql_text}")
                        results = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        plan_lines = []
                        for row in results:
                            plan_lines.append(" | ".join(f"{k}: {v}" for k, v in zip(columns, row)))
                        plan = "\n".join(plan_lines)
                    except Exception as e2:
                        logger.warning(f"Failed to get basic execution plan: {e2}")

        except Exception as e:
            logger.warning(f"Failed to connect to database for execution plan: {e}")
        finally:
            if conn:
                conn.close()

        return plan
