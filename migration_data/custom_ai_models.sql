-- 表 custom_ai_models 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 1
-- 列: id, user_id, model_name, model_display_name, api_base_url, api_key, is_active, last_test_status, last_test_time, created_at, updated_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `custom_ai_models` (`id`, `user_id`, `model_name`, `model_display_name`, `api_base_url`, `api_key`, `is_active`, `last_test_status`, `last_test_time`, `created_at`, `updated_at`) VALUES (12, 21, 'deepseek-chat', 'deepseek-chat', 'https://api.deepseek.com/v1', 'sk-ad0fe270505c46bab011cf672effe3b2', 1, 'success', '2025-11-12 14:38:51', '2025-11-10 05:37:27', '2025-11-12 14:37:42');

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `custom_ai_models`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `custom_ai_models` AUTO_INCREMENT = @max_id + 1;
