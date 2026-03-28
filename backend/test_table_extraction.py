#!/usr/bin/env python3
"""
测试复杂 SQL 的表名提取
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.sql_metadata_service import SQLMetadataService


def test_complex_sql_extraction():
    """
    测试复杂 SQL 的表名提取
    """
    metadata_service = SQLMetadataService()

    test_cases = [
        {
            "name": "简单查询",
            "sql": "SELECT * FROM users WHERE id > 100",
            "expected": ["users"]
        },
        {
            "name": "带 JOIN 查询",
            "sql": "SELECT * FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100",
            "expected": ["users", "orders"]
        },
        {
            "name": "子查询",
            "sql": "SELECT * FROM (SELECT * FROM users WHERE active = 1) u JOIN orders o ON u.id = o.user_id",
            "expected": ["users", "orders"]
        },
        {
            "name": "CTE 查询",
            "sql": """
WITH active_users AS (
    SELECT * FROM users WHERE active = 1
), recent_orders AS (
    SELECT * FROM orders WHERE order_date > '2023-01-01'
)
SELECT * FROM active_users u JOIN recent_orders o ON u.id = o.user_id
            """,
            "expected": ["users", "orders"]
        },
        {
            "name": "多 JOIN 查询",
            "sql": """
SELECT u.name, o.amount, p.product_name
FROM users u
INNER JOIN orders o ON u.id = o.user_id
LEFT JOIN order_items oi ON o.id = oi.order_id
RIGHT JOIN products p ON oi.product_id = p.id
WHERE o.order_date BETWEEN '2023-01-01' AND '2023-12-31'
            """,
            "expected": ["users", "orders", "order_items", "products"]
        },
        {
            "name": "复杂的 CTE 和子查询",
            "sql": """
WITH
    active_customers AS (
        SELECT customer_id, name
        FROM customers
        WHERE last_order_date > '2023-01-01'
    ),
    top_products AS (
        SELECT product_id, product_name, SUM(quantity) as total_sold
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY product_id, product_name
        ORDER BY total_sold DESC
        LIMIT 10
    ),
    customer_purchases AS (
        SELECT
            ac.customer_id,
            ac.name,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(o.total_amount) as total_spent
        FROM active_customers ac
        JOIN orders o ON ac.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN top_products tp ON oi.product_id = tp.product_id
        GROUP BY ac.customer_id, ac.name
    )
SELECT * FROM customer_purchases
WHERE total_spent > 1000
ORDER BY order_count DESC
            """,
            "expected": ["customers", "order_items", "products", "orders"]
        },
        {
            "name": "包含视图的查询",
            "sql": """
SELECT * FROM monthly_sales_report m
JOIN active_customers_view ac ON m.customer_id = ac.customer_id
WHERE m.year = 2023 AND m.month = 12
            """,
            "expected": ["monthly_sales_report", "active_customers_view"]
        }
    ]

    print("=" * 60)
    print("测试复杂 SQL 表名提取")
    print("=" * 60)

    all_passed = True

    for case in test_cases:
        print(f"\n测试: {case['name']}")
        print("-" * 40)
        print(f"SQL: {case['sql']}")
        try:
            result = metadata_service.extract_table_names(case['sql'])
            print(f"提取的表名: {result}")
            print(f"期望的表名: {case['expected']}")

            # 验证结果（忽略顺序）
            if set(result) == set(case['expected']):
                print("✅ 通过")
            else:
                print("❌ 失败 - 提取的表名不匹配")
                missing = set(case['expected']) - set(result)
                extra = set(result) - set(case['expected'])
                if missing:
                    print(f"   缺失的表名: {list(missing)}")
                if extra:
                    print(f"   多余的表名: {list(extra)}")
                all_passed = False
        except Exception as e:
            print(f"❌ 失败 - 错误: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过")
    else:
        print("❌ 有测试失败")

    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_complex_sql_extraction()
    sys.exit(0 if success else 1)
