-- =====================================================
-- 数据库迁移脚本
-- 添加文件夹管理功能支持
-- 执行日期: 2025-11-11
-- =====================================================

-- 检查表是否存在
-- SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'files' AND TABLE_SCHEMA = DATABASE();

-- 步骤 1: 为 files 表添加 folder_path 列
ALTER TABLE files 
ADD COLUMN folder_path VARCHAR(500) DEFAULT '/' NOT NULL COMMENT '文件所在的文件夹路径，默认根目录';

-- 步骤 2: 为 user_id 和 folder_path 创建复合索引（加快查询性能）
CREATE INDEX idx_files_user_folder ON files(user_id, folder_path);

-- 步骤 3: 验证迁移结果
-- 运行以下命令检查表结构（可选）
-- DESCRIBE files;
-- SHOW INDEXES FROM files;

-- =====================================================
-- 验证脚本（可选）
-- 运行以下查询验证迁移是否成功
-- =====================================================

-- 检查 folder_path 列是否存在
-- SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE, COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'files' AND COLUMN_NAME = 'folder_path' AND TABLE_SCHEMA = DATABASE();

-- 显示 files 表的所有列
-- SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'files' AND TABLE_SCHEMA = DATABASE()
-- ORDER BY ORDINAL_POSITION;

-- =====================================================
-- 数据恢复脚本（如果需要回滚）
-- =====================================================

-- 删除索引
-- DROP INDEX idx_files_user_folder ON files;

-- 删除列
-- ALTER TABLE files DROP COLUMN folder_path;

