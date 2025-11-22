-- 创建 user_folders 表
-- 此表用于管理用户创建的文件夹

CREATE TABLE IF NOT EXISTS `user_folders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `folder_path` VARCHAR(500) NOT NULL COMMENT '文件夹路径',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 外键约束
    CONSTRAINT `fk_user_folders_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    
    -- 唯一性约束：每个用户的文件夹路径唯一
    UNIQUE KEY `unique_user_folder_path` (`user_id`, `folder_path`),
    
    -- 索引
    KEY `idx_user_id` (`user_id`),
    KEY `idx_folder_path` (`folder_path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件夹表';

