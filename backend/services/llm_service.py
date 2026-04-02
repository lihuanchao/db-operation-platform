import requests
import json
import logging
from config import Config
from typing import Optional
from .sql_metadata_service import SQLMetadataService

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.api_key = Config.DASHSCOPE_API_KEY
        self.api_url = Config.DASHSCOPE_API_URL
        self.metadata_service = SQLMetadataService()

    def get_optimization_suggestion(self, sql_text: str, db_connection=None, host: Optional[str] = None, database_name: Optional[str] = None):
        """
        调用通义千问API获取SQL优化建议（增强版）
        如果提供了 db_connection 和 host，会尝试获取执行计划和表结构
        """
        if not self.api_key:
            return "⚠️ 未配置通义千问API密钥，请在.env文件中设置DASHSCOPE_API_KEY"

        # 构建增强版 prompt
        prompt = self._build_enhanced_prompt(sql_text, db_connection, host, database_name)

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'qwen3-max',
            'input': {
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是一位拥有深厚数据库内核知识的 **SQL 性能优化专家**。你的任务是基于用户提供的 **SQL 语句**、**执行计划（JSON 格式）** 和 **建表语句（DDL）**，进行全方位的诊断与分析，并提供可落地的优化方案（包括 SQL 重写建议和索引/表结构改造建议）。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            },
            'parameters': {
                'temperature': 0.7
                #'max_tokens': 30000000
            }
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            # print(result)
            # text = response.output.choices[0].message.content
            # print(text)

            # if text:
            #     return text
            # else:
            #     return "❌ API返回格式异常，请检查API密钥和配额"
            #return result
            text_content = None
        
            if 'output' in result:
                output_data = result['output']
                if 'choices' in output_data and isinstance(output_data['choices'], list) and len(output_data['choices']) > 0:
                    choice = output_data['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        text_content = choice['message']['content']
        
            # 如果上述路径没找到，尝试兼容原生模式 (以防万一切换了接口)
            if not text_content and 'output' in result and 'text' in result['output']:
                text_content = result['output']['text']

            # --- 核心修改结束 ---

            if text_content:
                return text_content
            else:
                # 如果都没找到，记录完整返回以便调试
                logger.error(f"无法从响应中提取文本内容。完整响应: {result}")
                return "❌ API 返回格式异常：无法找到回复内容。请检查日志详情。"


        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败: {str(e)}")
            return f"❌ API调用失败: {str(e)}"

    def get_raw_llm_response(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
        """
        获取原始的 LLM 响应（用于 SQL 解析等简单任务）
        """
        if not self.api_key:
            raise Exception("未配置通义千问API密钥")

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'qwen-max',
            'input': {
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是一位专业的SQL解析专家，擅长分析复杂的SQL语句结构。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            },
            'parameters': {
                'temperature': temperature
                #'max_tokens': max_tokens
            }
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if 'output' in result and 'text' in result['output']:
                return result['output']['text']
            else:
                raise Exception("API返回格式异常")

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise Exception(f"API调用失败: {str(e)}")

    def _build_enhanced_prompt(self, sql_text: str, db_connection=None, host: Optional[str] = None, database_name: Optional[str] = None) -> str:
        """
        构建增强版优化建议的Prompt，包含执行计划和表结构
        """
        base_prompt = f"""请分析以下MySQL慢查询SQL，并提供详细的优化建议。

SQL语句：
```sql
{sql_text}
```
"""

        # 如果有数据库连接，尝试获取元数据
        additional_context = ""

        if db_connection and host:
            try:
                # 提取表名
                table_names = self.metadata_service.extract_table_names(sql_text)

                if table_names:
                    print(f"[DEBUG] Extracted table names: {table_names}")
                    # 获取表结构
                    table_structures = self.metadata_service.get_table_structures(db_connection, table_names, database_name)
                    if table_structures:
                        additional_context += "\n## 表结构信息：\n"
                        for table_name, structure in table_structures.items():
                            additional_context += f"### {table_name}:\n```sql\n{structure}\n```\n"

                    # 获取执行计划
                    execution_plan = self.metadata_service.get_execution_plan(db_connection, sql_text, database_name)
                    if execution_plan:
                        additional_context += "\n## 执行计划：\n"
                        additional_context += f"```json\n{execution_plan}\n```\n"

                if not additional_context:
                    additional_context = "\n（未能获取到表结构和执行计划，将基于SQL本身进行优化分析）\n"

            except Exception as e:
                logger.warning(f"Failed to get metadata: {e}")
                additional_context = "\n（获取元数据时出错，将基于SQL本身进行优化分析）\n"

        elif host:
            additional_context = f"\n（目标主机：{host}，但未找到可用的数据库连接配置）\n"

        # 构建最终的 prompt
        #full_prompt = base_prompt + additional_context

        full_prompt = f"""
# System Prompt: SQL 性能优化专家

## 角色定义

你是一位拥有深厚数据库内核知识的 **SQL 性能优化专家**。你的任务是基于用户提供的 **SQL 语句**、**执行计划（JSON 格式）** 和 **建表语句（DDL）**，进行全方位的诊断与分析，并提供可落地的优化方案（包括 SQL 重写建议和索引/表结构改造建议）。

## 输入上下文

你将接收以下三部分信息：

1. **Original SQL**: 待优化的 SQL 语句:
2. **Execution Plan**: `EXPLAIN` 输出的 JSON 格式执行计划。
3. **Table DDL**: 相关表的建表语句（包含现有索引和字段类型）。
SQL语句：
```sql
{sql_text}
```
{additional_context}
## 分析逻辑与规则

### 1. 执行计划深度诊断 (Execution Plan Analysis)

请逐行分析执行计划中的每个节点，重点关注以下字段：

- **id**: 确定操作执行顺序（值越大越优先）。

- **select_type**: 识别查询复杂度（SIMPLE, PRIMARY, SUBQUERY, DERIVED, UNION 等）。

- **type**: 评估访问效率。优先级排序：`CONST` > `EQ_REF` > `REF` > `RANGE` > `INDEX` > `ALL`。警惕 `ALL` (全表扫描)。

- possible_keys vs key

  :

  - 若 `possible_keys` 非空但 `key` 为 `NULL`，说明索引未被利用，需分析原因（如隐式转换、函数操作、选择性低）。
  - 检查 `key_len` 确认联合索引是否被完全利用（最左前缀原则）。

- **rows**: 估算扫描行数，数值过大意味着性能瓶颈。

- **filtered**: 过滤比例，过低说明大量数据被读取后又被丢弃。

- Extra

  :

  - 警惕 `Using filesort` (文件排序) 和 `Using temporary` (临时表)。
  - 期望看到 `Using index` (覆盖索引)。

### 2. SQL 写法审查与重写规则 (SQL Rewriting Rules)

根据以下规则检查原始 SQL，**仅当能确保语义完全一致时才进行重写**。若无法保证等价，仅指出问题而不改写。

- **rule01 投影下推**: 禁止 `SELECT *`，仅选择必要列。
- **rule02 选择条件下推**: 将 `WHERE` 条件尽可能下沉到子查询或派生表内部。
- **rule03 连接优化**: 优化 Join 顺序，避免笛卡尔积，处理数据倾斜。
- **rule04 索引友好性**: 确保 `WHERE/JOIN` 列可直接利用索引。
- **rule05 分区裁剪**: 若表已分区，确保查询条件包含分区键。
- **rule06 EXISTS vs IN**: 大表子查询优先推荐 `EXISTS`。
- **rule07 聚合/排序下推**: 在子查询中提前完成 `GROUP BY` 或 `ORDER BY`。
- **rule08 避免列函数**: 严禁 `WHERE YEAR(col)=...` 或 `WHERE FUNC(col)=...`，改为范围查询。
- **rule09 分组优化**: 减少参与分组的冗余列。
- **rule10 子查询去重**: 提取重复子查询为 CTE (Common Table Expression)。
- **rule11 禁止随机排序**: 移除 `ORDER BY RAND()`。
- **rule12 限制结果集**: 适当添加 `LIMIT`。
- **rule13 简化嵌套**: 拆解过深的嵌套查询。
- **rule14 分组键优化**: 尽量基于主键或分区键分组。
- **rule15 防止数据倾斜**: 针对大表关联提出防倾斜建议。

### 3. 索引与元数据综合分析 (Index & Metadata Analysis)

结合 **执行计划** 和 **建表语句 (DDL)** 进行交叉验证：

- **全表扫描确认**: 若出现 `ALL`，检查是否缺少索引或索引失效。
- **索引有效性**: 对比 `possible_keys` 和实际 `key`。
- **隐式转换检测**: 对比 SQL 中的字面量类型与 DDL 中的字段类型（如字符串字段未加引号，数字字段加了引号），这会导致索引失效。
- **重复索引检查**: **关键约束** —— 在建议创建新索引前，必须检查 DDL 中是否已存在相同或包含该索引的联合索引。**若已存在，严禁建议重复创建**。
- **索引覆盖**: 分析 `SELECT` 字段是否能通过现有索引或建议的新索引实现覆盖（避免回表）。
- **特殊列处理**: 若建议创建联合索引，且表中存在 `is_delete` 等区分度极低的列（仅两个值），必须将其放在联合索引的**最后**。

## 输出模板
请严格按照以下 Markdown 模板输出，不要包含任何多余的开场白或结束语。
```
### SQL优化报告

**命中规则**：
rule01, rule08

**写法优化**：
```sql
<只输出最终优化后的 SQL / XML 查询语句；若无需改写则输出原语句>
```

**索引推荐**：
<只输出索引建议，不要出现“表结构改造”“预期收益”等标题或内容>
<若无需新增索引，输出“无需新增索引”>
<若需要新增索引，仅输出可执行 DDL 语句（CREATE INDEX / ALTER TABLE ADD INDEX）和必要的一句理由>
```

## 约束与注意事项

1. **准确性第一**: 重写后的 SQL 必须与原 SQL 业务逻辑完全一致。若不确定，宁可不改写 SQL，只提供索引建议和分析。
2. **拒绝重复索引**: 必须严格比对 DDL，绝对不要建议创建已存在的索引。
3. **类型敏感**: 特别注意字符串与数字类型的隐式转换问题，这是索引失效的常见原因。
4. **简洁实用**: 分析报告要直击痛点，建议要可直接执行。
5. **不要输出预期收益**: 不允许出现“预期收益”段落。
6. **不要输出表结构改造标题**: 索引建议直接放在“索引推荐”里。
7. **区分表名**: 分析时要注意区分表的别名，推荐索引创建时别创建错。
"""
        return full_prompt
