# 数据库迁移文件

## 迁移说明

本目录包含数据库结构变更的SQL脚本。

## 如何使用

### 方法1：手动执行（推荐）

1. 登录MySQL数据库：
```bash
mysql -u root -p
```

2. 选择数据库：
```sql
USE learning_companion;
```

3. 执行迁移脚本：
```sql
SOURCE py/migrations/add_custom_ai_models_table.sql;
```

### 方法2：使用命令行

```bash
mysql -u root -p learning_companion < py/migrations/add_custom_ai_models_table.sql
```

## 迁移文件列表

### add_custom_ai_models_table.sql
- **版本**: v8.1.0
- **日期**: 2025-01-09
- **说明**: 创建用户自定义AI模型表
- **影响**:
  - 新增 `custom_ai_models` 表
  - 添加外键关联到 `users` 表
  - 创建必要的索引

## 验证迁移

执行迁移后，可以使用以下SQL验证：

```sql
-- 查看表结构
DESC custom_ai_models;

-- 查看索引
SHOW INDEX FROM custom_ai_models;

-- 查看外键约束
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE
    TABLE_NAME = 'custom_ai_models'
    AND REFERENCED_TABLE_NAME IS NOT NULL;
```

## 回滚

如果需要回滚此迁移：

```sql
DROP TABLE IF EXISTS custom_ai_models;
```

⚠️ **警告**: 回滚操作将删除所有用户自定义模型数据！

## 注意事项

1. 执行迁移前建议先备份数据库
2. 确保在非生产高峰期执行
3. 迁移后测试相关功能
4. 记录迁移执行时间和结果

