import unittest

from services.optimization_task_service import OptimizationTaskService


class OptimizationTaskServiceTestCase(unittest.TestCase):
    def test_extract_sections_with_markdown_headings(self):
        suggestion = """
### SQL优化报告

**命中规则**：
rule01, rule08

**写法优化**：

### SQL重写
```sql
SELECT id, name FROM user WHERE status = 1;
```

### 索引推荐
CREATE INDEX idx_user_status ON user(status);
命中规则：rule04

**预期收益**：
▸ 执行耗时：100ms -> 20ms
        """.strip()

        writing, index, optimized, matched_rules = OptimizationTaskService.extract_sections(suggestion)
        self.assertIn('SELECT id, name FROM user WHERE status = 1;', writing)
        self.assertIn('CREATE INDEX idx_user_status ON user(status);', index)
        self.assertNotIn('命中规则', index)
        self.assertNotIn('预期收益', index)
        self.assertEqual(optimized, 'SELECT id, name FROM user WHERE status = 1;')
        self.assertEqual(matched_rules, 'rule01, rule08, rule04')

    def test_extract_sections_falls_back_when_missing_headings(self):
        suggestion = """
建议如下：
ALTER TABLE orders ADD INDEX idx_orders_create_time(create_time);
        """.strip()

        writing, index, optimized, matched_rules = OptimizationTaskService.extract_sections(suggestion)
        self.assertIn('建议如下', writing)
        self.assertIn('ALTER TABLE orders ADD INDEX idx_orders_create_time(create_time);', index)
        self.assertIsNone(optimized)
        self.assertEqual(matched_rules, '')

    def test_normalize_index_recommendation_only_sql(self):
        content = """
**索引推荐**：
建议新增复合索引以减少回表。
ALTER TABLE users
ADD INDEX idx_users_status_created_at (status, created_at);
命中规则：rule04
        """.strip()

        result = OptimizationTaskService._normalize_index_recommendation(content)
        self.assertIn('ALTER TABLE users', result)
        self.assertIn('ADD INDEX idx_users_status_created_at (status, created_at);', result)
        self.assertNotIn('命中规则', result)
        self.assertNotIn('建议新增复合索引', result)

    def test_extract_optimized_content_ignores_ddl_code_block(self):
        suggestion = """
### SQL优化报告

**优化方案**：
```sql
SELECT id, name FROM users WHERE status = 1;
```

**索引推荐**：
```sql
CREATE TABLE tmp_users (id bigint);
CREATE INDEX idx_users_status ON users(status);
```
        """.strip()

        writing, index, optimized, matched_rules = OptimizationTaskService.extract_sections(suggestion)
        self.assertIn('SELECT id, name FROM users WHERE status = 1;', optimized or '')
        self.assertIn('CREATE INDEX idx_users_status ON users(status);', index)
        self.assertEqual(matched_rules, '')


if __name__ == '__main__':
    unittest.main()
