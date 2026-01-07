-- 表 user_folders 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 3
-- 列: id, user_id, folder_path, created_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `user_folders` (`id`, `user_id`, `folder_path`, `created_at`) VALUES (18, 21, '/123/', '2025-11-12 10:24:31');
INSERT IGNORE INTO `user_folders` (`id`, `user_id`, `folder_path`, `created_at`) VALUES (21, 21, '/大疆/', '2025-11-12 10:25:28');
INSERT IGNORE INTO `user_folders` (`id`, `user_id`, `folder_path`, `created_at`) VALUES (22, 21, '/123/321/', '2025-11-12 13:05:11');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `user_folders`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `user_folders` AUTO_INCREMENT = @max_id + 1;
