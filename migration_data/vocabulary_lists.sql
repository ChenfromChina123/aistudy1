-- 表 vocabulary_lists 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 6
-- 列: id, name, description, is_preset, is_public, created_by, created_at, updated_at, language

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (1, '基础英语单词', '适合初学者的常用英语单词', 1, 1, NULL, '2025-11-01 13:21:04', '2025-11-01 13:21:04', 'en');
INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (2, '旅游英语词汇', '旅游出行必备英语词汇', 1, 1, NULL, '2025-11-01 13:21:04', '2025-11-01 13:21:04', 'en');
INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (3, '商务英语常用词', '职场商务场景常用英语单词', 1, 1, NULL, '2025-11-01 13:21:04', '2025-11-01 13:21:04', 'en');
INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (19, '单词', '上传的单词表: 单词', 0, 0, 1, '2025-11-02 16:53:45', '2025-11-02 16:53:45', 'en');
INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (24, '单词', '上传的单词表: 单词', 0, 0, 15, '2025-11-04 03:53:43', '2025-11-04 03:53:43', 'en');
INSERT IGNORE INTO `vocabulary_lists` (`id`, `name`, `description`, `is_preset`, `is_public`, `created_by`, `created_at`, `updated_at`, `language`) VALUES (25, '单词', '上传的单词表: 单词', 0, 0, 21, '2025-11-05 15:19:07', '2025-11-05 15:19:07', 'en');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `vocabulary_lists`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `vocabulary_lists` AUTO_INCREMENT = @max_id + 1;
