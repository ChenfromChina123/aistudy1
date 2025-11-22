-- 表 user_settings 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 2
-- 列: id, user_id, model_name, api_base, api_key, model_params, created_at, updated_at

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `user_settings` (`id`, `user_id`, `model_name`, `api_base`, `api_key`, `model_params`, `created_at`, `updated_at`) VALUES (1, 15, '', 'admin@example.com', 'admin', NULL, '2025-10-31 11:11:41', '2025-10-31 11:17:58');
INSERT IGNORE INTO `user_settings` (`id`, `user_id`, `model_name`, `api_base`, `api_key`, `model_params`, `created_at`, `updated_at`) VALUES (2, 21, NULL, '3301767269@qq.com', '12345678', '{"temperature":0.2,"max_tokens":1300,"top_p":0}', '2025-11-09 10:05:01', '2025-11-12 15:27:57');

SET FOREIGN_KEY_CHECKS = 1;
