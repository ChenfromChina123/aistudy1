-- 表 verification_codes 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 1
-- 列: id, email, code, expiration_time, created_time, is_blocked, blocked_until

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `verification_codes` (`id`, `email`, `code`, `expiration_time`, `created_time`, `is_blocked`, `blocked_until`) VALUES (54, '1836078388@qq.com', '324614', '2025-11-13 08:12:31', '2025-11-13 08:07:31', 0, NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `verification_codes`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `verification_codes` AUTO_INCREMENT = @max_id + 1;
