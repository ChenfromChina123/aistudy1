-- 表 users 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 6
-- 列: id, username, email, password_hash, avatar, created_at, updated_at, is_active, last_login

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (4, 'dsas', '3274497954@qq.com', 'scrypt:32768:8:1$bqbevO9oIpg11ERY$eec64f5c9d016556594d85cf09c5a9db66cd58eff8c98873d3be795c253fdf3ec850fc79db199ffc976d0ca83ab07a3f7031f656009ae5a3ef33eb2ba3569d40', NULL, '2025-10-12 09:44:17', '2025-10-12 09:44:17', 1, NULL);
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (15, 'admin', 'admin@example.com', 'scrypt:32768:8:1$jg96wW67T7ACRia4$248cdc2eb7b274ecd9d5710bb5700d01716cd5bcc8b8c6f86c7fe7842113a2d948665dd8f8012d28eed7472f1b0157c9008e6d4c5c05d220230102b13a9aab41', NULL, '2025-10-17 06:42:51', '2025-11-01 07:57:02', 1, NULL);
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (16, 'dbtest_onoscxe5', 'db_test_q7j08d@example.com', 'scrypt:32768:8:1$49oa5Ew2X10SiRez$a4aa521fad3213ade42e185efdcd47f30330038ede69333f04bc048828a44d2e72b0b83cc3db9fb66835c28757037a8a5b9b27cb2a0bbcf1515e7bbd4aa7ef0c', NULL, '2025-10-17 14:33:18', '2025-10-17 14:33:18', 1, NULL);
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (21, '小小guaigaui11', '3301767269@qq.com', 'scrypt:32768:8:1$6l4PO3BGl43B7ncw$bfecbef95437752006b8ed86a7393fd3ee2f16a3c15f1d4e4cbaf97653d4336aec2e6c087bef5351354c8f7e46bd5cc2c21f76e7edde5c06b72003d5e7ca8a76', '/api/users/avatar/21_92b323552eef4022a69a94ecd2b506a8.jpg', '2025-10-22 09:38:05', '2025-11-12 14:31:02', 1, NULL);
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (25, 'ggfg', '1234567788@qq.com', 'scrypt:32768:8:1$0KpDwlPfv3dqEhkk$9281597a166082fb3c800f085a1dcace9efd6f0405fb790de4008019e3c4fdd876d561c6e2bfae8a3274a3ba4ce4c395d32ab5a1530ac5c98531eb6c1c4f24eb', NULL, '2025-10-31 10:23:01', '2025-10-31 10:23:01', 1, NULL);
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `avatar`, `created_at`, `updated_at`, `is_active`, `last_login`) VALUES (26, '1111', '1836078388@qq.com', 'scrypt:32768:8:1$Linhdsl5JmLIqs5O$8031c8bfffc5a1dfc64e993ecfb1f0b684a5ef77a18b98f551e4117fb7c0448c2221f23b0d0478865ebf5c030c292e7d498cb2abf0d351e8ee4f5aacc3cb6913', NULL, '2025-11-13 08:05:39', '2025-11-13 08:05:39', 1, NULL);

SET FOREIGN_KEY_CHECKS = 1;

-- 重置自增ID
SELECT @max_id := MAX(id) FROM `users`;
SET @max_id = IFNULL(@max_id, 0);
ALTER TABLE `users` AUTO_INCREMENT = @max_id + 1;
