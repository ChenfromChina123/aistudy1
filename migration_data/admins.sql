-- 表 admins 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 1
-- 列: id, user_id, is_active, created_at, updated_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `admins` (`id`, `user_id`, `is_active`, `created_at`, `updated_at`) VALUES (1, 15, 1, NULL, NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `admins`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `admins` AUTO_INCREMENT = @max_id + 1;
