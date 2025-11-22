-- 表 notes 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 1
-- 列: id, title, file_path, created_at, updated_at, user_id

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `notes` (`id`, `title`, `file_path`, `created_at`, `updated_at`, `user_id`) VALUES (1, '英语笔记', 'd:\\基于IPv6的AI智能学习伴侣导师\\基于IPv6的AI智能学习伴侣导师8.0\\py\\cloud_disk\\15\\notes\\0c60c054-979f-49b8-be46-6aa5a993e9bd.txt', '2025-11-01 10:36:04', '2025-11-01 10:39:28', 15);

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `notes`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `notes` AUTO_INCREMENT = @max_id + 1;
