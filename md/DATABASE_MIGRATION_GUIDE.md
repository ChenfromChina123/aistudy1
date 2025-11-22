# 数据库迁移指南 - 文件夹功能

## ❌ 错误信息

```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (1054, "Unknown column 'files.folder_path' in 'field list'")
```

## 🔍 问题原因

代码中已添加了 `folder_path` 字段到 `UserFile` 模型，但数据库中的实际表还没有这个列。

## ✅ 解决方案

### 方案 1: 使用自动迁移脚本（推荐）

这是最简便的方法，脚本会自动检查并添加必要的列。

**步骤**：

1. 确保已配置 `.env` 文件中的 `DATABASE_URL`

2. 运行迁移脚本：

```bash
cd py/
python migrate_add_folder_path.py
```

3. 脚本会自动：
   - 连接到数据库
   - 检查列是否已存在
   - 添加 `folder_path` 列
   - 创建索引以提高查询性能
   - 验证迁移结果

4. 查看输出信息确认迁移成功：

```
============================================================
开始数据库迁移：添加 folder_path 列
============================================================
[INFO] 使用数据库URL: mysql+pymysql://***@***
[INFO] 正在添加 folder_path 列...
[OK] 列添加成功
[INFO] 正在创建索引...
[OK] 索引创建成功

[SUCCESS] 数据库迁移完成！

============================================================
验证迁移结果
============================================================
[INFO] files 表现有列数: XX
  - id: INTEGER
  - file_uuid: VARCHAR(36)
  - original_name: VARCHAR(255)
  - save_path: VARCHAR(255)
  - file_size: INTEGER
  - file_type: VARCHAR(50)
  - upload_time: DATETIME
  - user_id: INTEGER
  - folder_path: VARCHAR(500)

[SUCCESS] folder_path 列已成功添加！
```

### 方案 2: 手动 SQL 执行

如果自动迁移脚本遇到问题，可以手动执行 SQL。

**步骤**：

1. 连接到 MySQL 数据库（推荐使用 MySQL Workbench 或命令行）：

```bash
mysql -h localhost -u root -p
```

2. 选择数据库：

```sql
USE ipv6_education;  -- 替换为你的数据库名
```

3. 执行迁移 SQL：

```sql
-- 添加 folder_path 列
ALTER TABLE files 
ADD COLUMN folder_path VARCHAR(500) DEFAULT '/' NOT NULL 
COMMENT '文件所在的文件夹路径，默认根目录';

-- 创建索引
CREATE INDEX idx_files_user_folder ON files(user_id, folder_path);
```

4. 验证迁移结果：

```sql
-- 查看表结构
DESCRIBE files;

-- 查看索引
SHOW INDEXES FROM files;

-- 检查 folder_path 列
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'files' AND TABLE_SCHEMA = DATABASE()
ORDER BY ORDINAL_POSITION;
```

### 方案 3: 使用 SQL 文件

我们提供了一个 SQL 文件 `migrations/add_folder_path.sql`，包含所有必要的命令。

**使用 MySQL 命令行**：

```bash
mysql -h localhost -u root -p ipv6_education < py/migrations/add_folder_path.sql
```

**使用 MySQL Workbench**：

1. 打开 MySQL Workbench
2. 连接到数据库
3. 打开文件 `py/migrations/add_folder_path.sql`
4. 执行文件内容

## 📋 验证迁移

执行以下查询确认迁移成功：

```sql
-- 检查 folder_path 列是否存在和类型是否正确
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'files' AND COLUMN_NAME = 'folder_path';

-- 预期输出:
-- COLUMN_NAME: folder_path
-- COLUMN_TYPE: varchar(500)
-- COLUMN_DEFAULT: /
-- IS_NULLABLE: NO
-- COLUMN_COMMENT: 文件所在的文件夹路径，默认根目录
```

## 🔄 后续步骤

1. 迁移完成后，重启后端服务：

```bash
# 停止现有服务（如果正在运行）
Ctrl+C

# 重新启动
python py/run.py
```

2. 测试功能：

```bash
# 测试获取文件列表（应该不再报错）
curl http://localhost:5000/api/cloud_disk/files?user_id=YOUR_USER_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 测试创建文件夹
curl -X POST http://localhost:5000/api/cloud_disk/create-folder \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"folder_path": "/test/"}'
```

## ⚠️ 常见问题

### Q1: 迁移脚本报错"连接失败"

**原因**：`DATABASE_URL` 环境变量配置错误或数据库未运行

**解决**：
- 检查 `.env` 文件中的 `DATABASE_URL` 是否正确
- 确保 MySQL 服务已启动
- 确保用户名和密码正确

### Q2: SQL 执行报错"表不存在"

**原因**：数据库或表名错误

**解决**：
- 使用正确的数据库名称
- 检查表是否真的存在：`SHOW TABLES;`

### Q3: 迁移后仍然报错

**原因**：可能后端服务缓存了旧的模型信息

**解决**：
- 完全停止后端服务
- 删除 `__pycache__` 目录
- 重新启动服务

### Q4: 如何回滚迁移？

**使用自动脚本回滚**：暂无自动回滚脚本，建议手动执行以下 SQL：

```sql
-- 删除索引
DROP INDEX idx_files_user_folder ON files;

-- 删除列
ALTER TABLE files DROP COLUMN folder_path;
```

**或者从备份恢复**。

## 📞 技术支持

如果遇到迁移问题，请：

1. 检查错误信息中的具体错误代码
2. 查看本文件的相关部分
3. 查看后端日志获取更多信息
4. 确保所有依赖都已正确安装

## 📊 迁移检查清单

- [ ] `.env` 文件已配置正确的 `DATABASE_URL`
- [ ] MySQL 服务已启动
- [ ] 已选择正确的数据库
- [ ] 运行了迁移脚本或 SQL 文件
- [ ] 迁移验证查询显示 `folder_path` 列已存在
- [ ] 后端服务已重启
- [ ] 测试 API 调用正常工作
- [ ] 云盘功能可以正常使用

## 📝 相关文件

- 自动迁移脚本：`py/migrate_add_folder_path.py`
- SQL 迁移脚本：`py/migrations/add_folder_path.sql`
- 功能更新文档：`FEATURE_UPDATE_20251111.md`
- 部署检查清单：`DEPLOYMENT_CHECKLIST.md`

