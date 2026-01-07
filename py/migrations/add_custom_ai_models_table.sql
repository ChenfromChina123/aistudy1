-- 创建用户自定义AI模型表
CREATE TABLE IF NOT EXISTS custom_ai_models (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id INT NOT NULL COMMENT '用户ID',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    model_display_name VARCHAR(100) NOT NULL COMMENT '模型显示名称',
    api_base_url VARCHAR(500) NOT NULL COMMENT 'API基础URL',
    api_key VARCHAR(500) NOT NULL COMMENT 'API密钥',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    last_test_status VARCHAR(20) DEFAULT NULL COMMENT '最后测试状态: success/failed',
    last_test_time DATETIME DEFAULT NULL COMMENT '最后测试时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_model_name (model_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户自定义AI模型表';

