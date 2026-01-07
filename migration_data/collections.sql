-- 表 collections 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 25
-- 列: id, user_id, resource_id, created_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (1, 4, 1, '2025-11-03 16:20:50');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (2, 4, 2, '2025-11-03 16:20:50');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (3, 4, 3, '2025-11-03 16:20:50');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (4, 4, 4, '2025-11-03 16:20:50');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (5, 4, 5, '2025-11-03 16:20:50');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (6, 15, 1, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (7, 15, 2, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (8, 15, 3, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (9, 15, 4, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (10, 15, 5, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (11, 16, 1, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (12, 16, 2, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (13, 16, 3, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (14, 16, 4, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (15, 16, 5, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (16, 21, 1, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (17, 21, 2, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (18, 21, 3, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (19, 21, 4, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (20, 21, 5, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (21, 25, 1, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (22, 25, 2, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (23, 25, 3, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (24, 25, 4, '2025-11-03 08:21:25');
INSERT IGNORE INTO `collections` (`id`, `user_id`, `resource_id`, `created_at`) VALUES (25, 25, 5, '2025-11-03 08:21:25');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `collections`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `collections` AUTO_INCREMENT = @max_id + 1;
