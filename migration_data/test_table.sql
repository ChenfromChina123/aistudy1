-- 表 test_table 数据导出
-- 导出时间: 2025-11-13 22:12:55
-- 总记录数: 2
-- 列: id, name

SET FOREIGN_KEY_CHECKS = 0;

INSERT IGNORE INTO `test_table` (`id`, `name`) VALUES (1, 'test');
INSERT IGNORE INTO `test_table` (`id`, `name`) VALUES (2, 'test');

SET FOREIGN_KEY_CHECKS = 1;
