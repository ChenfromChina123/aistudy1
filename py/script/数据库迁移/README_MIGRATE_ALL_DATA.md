# 数据库完整迁移脚本使用说明

## 概述

`migrate_all_data.py` 是一个完整的数据库迁移脚本，用于将源数据库的所有数据迁移到目标数据库。该脚本支持：

- ✅ 自动处理外键依赖关系
- ✅ 按正确顺序迁移表
- ✅ 批量处理大量数据
- ✅ 错误处理和日志记录
- ✅ 数据验证和统计
- ✅ 支持MySQL数据库

## 功能特性

### 1. 自动表顺序管理
脚本按照外键依赖关系自动确定表的迁移顺序：
- 第一层：基础表（users, categories等）
- 第二层：依赖基础表的表
- 第三层：依赖其他表的表

### 2. 支持的表
脚本支持迁移以下所有表：
- 用户相关：users, admins, verification_codes, custom_ai_models
- 文件相关：user_folders, user_files, file_shares
- 聊天相关：chat_sessions, chat_records
- 资源相关：categories, resources, collections, public_resources
- 反馈相关：feedbacks
- 笔记相关：notes
- 语言学习相关：vocabulary_lists, vocabulary_words, user_word_progress, public_vocabulary_words, user_learning_records, generated_articles, article_used_words, vocabulary_upload_tasks

### 3. 安全特性
- 使用 `INSERT IGNORE` 避免重复数据
- 自动禁用/启用外键检查
- 事务支持，失败自动回滚
- 详细的错误日志

## 使用方法

### 基本用法

```bash
python py/script/migrate_all_data.py \
    --source-db "mysql+pymysql://user:password@host:port/source_database" \
    --target-db "mysql+pymysql://user:password@host:port/target_database"
```

### 参数说明

- `--source-db`: 源数据库连接URL（必需）
- `--target-db`: 目标数据库连接URL（必需）
- `--tables`: 要迁移的表列表（可选，默认迁移所有表）
- `--batch-size`: 批量处理大小（可选，默认1000）

### 示例

#### 1. 迁移所有数据

```bash
python py/script/migrate_all_data.py \
    --source-db "mysql+pymysql://root:123456@localhost:3306/old_database" \
    --target-db "mysql+pymysql://root:123456@localhost:3306/new_database"
```

#### 2. 只迁移特定表

```bash
python py/script/migrate_all_data.py \
    --source-db "mysql+pymysql://root:123456@localhost:3306/old_database" \
    --target-db "mysql+pymysql://root:123456@localhost:3306/new_database" \
    --tables users admins user_files
```

#### 3. 自定义批量大小

```bash
python py/script/migrate_all_data.py \
    --source-db "mysql+pymysql://root:123456@localhost:3306/old_database" \
    --target-db "mysql+pymysql://root:123456@localhost:3306/new_database" \
    --batch-size 500
```

## 数据库URL格式

MySQL数据库URL格式：
```
mysql+pymysql://用户名:密码@主机:端口/数据库名
```

示例：
```
mysql+pymysql://root:123456@localhost:3306/ipv6_education
mysql+pymysql://admin:password@192.168.1.100:3306/production_db
```

## 迁移流程

1. **连接检查**: 验证源数据库和目标数据库连接
2. **表发现**: 自动发现源数据库中的所有表
3. **顺序确定**: 根据外键依赖关系确定迁移顺序
4. **数据迁移**: 按顺序迁移每个表的数据
5. **验证**: 验证迁移结果
6. **统计**: 生成迁移摘要报告

## 日志文件

脚本会在 `log/` 目录下生成日志文件：
```
log/migrate_all_data_YYYYMMDD_HHMMSS.log
```

日志包含：
- 迁移进度
- 成功/失败的记录
- 错误信息
- 统计摘要

## 注意事项

### 1. 备份数据
⚠️ **重要**: 在执行迁移前，请务必备份目标数据库！

```bash
# 备份目标数据库
mysqldump -u root -p target_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. 数据库结构
- 目标数据库必须已经创建
- 目标数据库的表结构应该与源数据库一致
- 建议先执行表结构迁移，再执行数据迁移

### 3. 外键约束
- 脚本会自动处理外键检查
- 如果目标数据库已有数据，可能会因为外键约束导致部分记录无法插入

### 4. 自增ID
- 脚本会自动重置自增ID
- 确保新插入的记录ID不会冲突

### 5. 重复数据
- 使用 `INSERT IGNORE` 避免重复插入
- 如果主键或唯一键冲突，会跳过该记录

## 迁移顺序

脚本按照以下顺序迁移表（考虑外键依赖）：

1. **基础表**（无外键依赖）
   - users
   - categories
   - vocabulary_lists
   - public_vocabulary_words
   - vocabulary_upload_tasks

2. **依赖users的表**
   - admins
   - verification_codes
   - custom_ai_models
   - notes
   - user_folders
   - user_files
   - chat_sessions
   - resources
   - feedbacks
   - user_learning_records
   - generated_articles

3. **依赖其他表的表**
   - file_shares (依赖 user_files, users)
   - chat_records (依赖 chat_sessions, users)
   - collections (依赖 users, resources)
   - public_resources (依赖 resources)
   - vocabulary_words (依赖 vocabulary_lists)
   - user_word_progress (依赖 vocabulary_words, users)
   - article_used_words (依赖 generated_articles, vocabulary_words)

## 故障排除

### 问题1: 连接失败
```
错误: 数据库连接失败
解决: 检查数据库URL、用户名、密码、主机和端口
```

### 问题2: 表不存在
```
警告: 表 xxx 在源数据库中不存在，跳过
解决: 这是正常的，如果表不存在会跳过
```

### 问题3: 外键约束错误
```
错误: Cannot add or update a child row: a foreign key constraint fails
解决: 确保依赖的表已经迁移完成，检查迁移顺序
```

### 问题4: 字符编码问题
```
错误: Incorrect string value
解决: 确保数据库使用utf8mb4字符集
```

## 性能优化

### 1. 批量大小
- 默认批量大小为1000
- 对于大表，可以增加批量大小（如5000）
- 对于小表，可以减少批量大小（如100）

### 2. 网络延迟
- 如果源数据库和目标数据库在不同服务器，考虑网络延迟
- 可以适当减少批量大小

### 3. 内存使用
- 大批量处理会占用更多内存
- 如果内存不足，减少批量大小

## 验证迁移结果

迁移完成后，可以执行以下SQL验证：

```sql
-- 比较记录数
SELECT 
    'users' as table_name,
    (SELECT COUNT(*) FROM source_db.users) as source_count,
    (SELECT COUNT(*) FROM target_db.users) as target_count
UNION ALL
SELECT 
    'user_files',
    (SELECT COUNT(*) FROM source_db.user_files),
    (SELECT COUNT(*) FROM target_db.user_files);

-- 检查数据完整性
SELECT * FROM target_db.users LIMIT 10;
SELECT * FROM target_db.user_files LIMIT 10;
```

## 示例输出

```
2025-01-15 10:30:00 - INFO - ================================================================================
2025-01-15 10:30:00 - INFO - 开始数据库迁移
2025-01-15 10:30:00 - INFO - 源数据库: localhost:3306/old_database
2025-01-15 10:30:00 - INFO - 目标数据库: localhost:3306/new_database
2025-01-15 10:30:00 - INFO - ================================================================================
2025-01-15 10:30:01 - INFO - ✓ 源数据库连接成功
2025-01-15 10:30:01 - INFO - ✓ 目标数据库连接成功
2025-01-15 10:30:01 - INFO - 将迁移 23 个表
2025-01-15 10:30:01 - INFO - --------------------------------------------------------------------------------
2025-01-15 10:30:01 - INFO - 
[1/23] 迁移表: users
2025-01-15 10:30:01 - INFO - 开始迁移表 users，源记录数: 150
2025-01-15 10:30:02 - INFO -   已迁移 150/150 条记录
2025-01-15 10:30:02 - INFO - ✓ 表 users 迁移完成: 150 条记录
...
2025-01-15 10:35:00 - INFO - ================================================================================
2025-01-15 10:35:00 - INFO - 迁移摘要
2025-01-15 10:35:00 - INFO - ================================================================================
2025-01-15 10:35:00 - INFO - 总表数: 23
2025-01-15 10:35:00 - INFO - 成功迁移: 23
2025-01-15 10:35:00 - INFO - 失败表数: 0
2025-01-15 10:35:00 - INFO - 总记录数: 15234
2025-01-15 10:35:00 - INFO - 成功迁移记录数: 15234
2025-01-15 10:35:00 - INFO - 失败记录数: 0
2025-01-15 10:35:00 - INFO - ================================================================================
2025-01-15 10:35:00 - INFO - 
✓ 数据库迁移完成！
```

## 联系支持

如果遇到问题，请：
1. 查看日志文件获取详细错误信息
2. 检查数据库连接和权限
3. 验证表结构是否一致
4. 查看本文档的故障排除部分

