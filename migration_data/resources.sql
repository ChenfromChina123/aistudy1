-- 表 resources 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 7
-- 列: id, category_id, title, url, description, is_public, created_at, updated_at, type, view_count, download_count, file_path, user_id

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (1, 1, '微积分精讲课程', 'https://pan.baidu.com/s/1uE22dq1lnymU0h3YrlFngg?pwd=8888', '清华大学微积分完整课程视频', 1, '2025-10-17 14:21:20', '2025-10-17 14:21:20', 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (2, 1, '导数计算器', 'https://www.runoob.com/python/python-tutorial.htmle', '在线导数计算与可视化工具', 1, '2025-10-17 14:21:20', '2025-10-17 14:21:20', 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (3, 2, 'Python入门教程', 'https://www.bilibili.com/video/BV1hx41167mE/', '浙江大学Python编程基础课程', 1, '2025-10-17 14:21:20', '2025-10-17 14:21:20', 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (4, 3, '量子力学基础讲座', 'http://[2001:da8:202:10::36]/physics/quantum_basic.mp4', '北京大学物理学院量子力学入门讲座', 1, '2025-10-17 14:21:20', '2025-10-17 14:21:20', 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (5, 3, '双缝实验模拟', 'http://[2001:da8:8000:1::1234]/simulations/double-slit', '交互式双缝实验模拟工具', 1, '2025-10-17 14:21:20', '2025-10-17 14:21:20', 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (21, 10, 'deepseek开放平台', 'https://platform.deepseek.com/api_keys', '', 0, '2025-11-10 03:30:05', NULL, 'LINK', 0, 0, NULL, NULL);
INSERT IGNORE INTO `resources` (`id`, `category_id`, `title`, `url`, `description`, `is_public`, `created_at`, `updated_at`, `type`, `view_count`, `download_count`, `file_path`, `user_id`) VALUES (22, 11, 'gihub', 'https://github.com/', '', 0, '2025-11-10 03:50:39', NULL, 'LINK', 0, 0, NULL, NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `resources`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `resources` AUTO_INCREMENT = @max_id + 1;
