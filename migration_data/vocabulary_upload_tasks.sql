-- 表 vocabulary_upload_tasks 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 2
-- 列: id, task_id, user_id, vocabulary_list_id, status, progress, total_words, processed_words, message, error_message, created_at, updated_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `vocabulary_upload_tasks` (`id`, `task_id`, `user_id`, `vocabulary_list_id`, `status`, `progress`, `total_words`, `processed_words`, `message`, `error_message`, `created_at`, `updated_at`) VALUES (1, 'e958c786-1cdd-4892-8ce5-731c1b59fcc5', 15, 24, 'completed', 100, 214, 114, '处理完成！共处理 214 个单词，其中 2 个来自总表，112 个由AI处理', NULL, '2025-11-04 03:53:43', '2025-11-04 03:53:43');
INSERT IGNORE INTO `vocabulary_upload_tasks` (`id`, `task_id`, `user_id`, `vocabulary_list_id`, `status`, `progress`, `total_words`, `processed_words`, `message`, `error_message`, `created_at`, `updated_at`) VALUES (2, '068eb1ca-d736-423f-ae39-53542afb126a', 21, 25, 'completed', 100, 213, 205, '处理完成！共处理 213 个单词，其中 113 个来自总表，92 个由AI处理', NULL, '2025-11-05 15:19:07', '2025-11-05 15:19:07');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `vocabulary_upload_tasks`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `vocabulary_upload_tasks` AUTO_INCREMENT = @max_id + 1;
