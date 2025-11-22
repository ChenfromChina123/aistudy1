-- 表 categories 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 11
-- 列: id, name, description, created_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (1, '微积分', '高等数学中的微积分相关资源', '2025-10-17 13:56:46');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (2, '编程', '各种编程语言学习资源', '2025-10-17 13:56:46');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (3, '量子力学', '物理学中的量子力学相关资源', '2025-10-17 13:56:46');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (4, '萨达', NULL, '2025-10-17 14:43:55');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (5, '测试分类_bz9gONFc', NULL, '2025-10-17 14:43:55');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (6, '测试分类_LquL4U29', NULL, '2025-10-17 14:43:55');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (7, '测试分类', NULL, NULL);
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (8, '111', NULL, '2025-10-17 15:15:30');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (9, '大撒大撒', NULL, '2025-10-18 13:51:21');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (10, 'AI接口平台', NULL, '2025-11-10 03:30:05');
INSERT IGNORE INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES (11, '代码开发平台', NULL, '2025-11-10 03:50:39');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `categories`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `categories` AUTO_INCREMENT = @max_id + 1;
