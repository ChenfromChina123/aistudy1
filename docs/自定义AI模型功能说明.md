# 自定义AI模型功能说明

## 功能概述

用户可以添加和管理自己的AI模型API，支持任何兼容OpenAI API格式的模型服务。

## 功能特性

### 1. 添加自定义模型
- 支持添加任意数量的自定义AI模型
- 需要提供：
  - **模型名称**：如 `gpt-4`, `claude-3`, 自定义模型名等
  - **模型显示名称**：在界面上显示的友好名称
  - **API地址**：API基础URL（如 `https://api.openai.com/v1`）
  - **API密钥**：访问API所需的密钥

### 2. API连通性测试
- 添加模型前可以测试API连接
- 测试功能会：
  - 自动调用API进行简单测试
  - 验证API密钥是否有效
  - 检查模型是否可用
  - 显示测试结果（成功/失败）

### 3. 模型管理
- **查看模型列表**：显示所有已添加的模型
- **测试连接**：随时重新测试模型连接状态
- **删除模型**：删除不需要的模型
- **状态显示**：
  - ✓ 测试成功（绿色标记）
  - ✗ 测试失败（红色标记）

### 4. 集成到聊天界面
- 自定义模型会自动出现在主页面的AI模型选择器中
- 以分组形式显示："我的自定义模型"
- 成功测试的模型会显示 ✓ 标记
- 可以像使用内置模型一样使用自定义模型

## 使用步骤

### 步骤1：打开用户设置
1. 点击右上角"个人中心"
2. 点击"用户设置"
3. 切换到"AI模型"标签页

### 步骤2：添加模型
1. 填写模型信息：
   ```
   AI模型名称: gpt-4
   API地址: https://api.openai.com/v1
   API密钥: sk-your-api-key-here
   ```

2. 点击"测试连接"按钮：
   - 系统会自动添加模型并测试
   - 测试成功后保留模型
   - 测试失败会删除模型，需要检查配置后重试

3. 或者直接点击"添加模型"：
   - 不进行测试，直接添加
   - 后续可以手动测试

### 步骤3：使用模型
1. 回到主页面
2. 在"AI模型"下拉列表中选择你的自定义模型
3. 开始对话

## 数据库结构

### custom_ai_models 表
```sql
- id: 主键
- user_id: 用户ID（外键）
- model_name: 模型名称
- model_display_name: 显示名称
- api_base_url: API基础URL
- api_key: API密钥（加密存储）
- is_active: 是否启用
- last_test_status: 最后测试状态
- last_test_time: 最后测试时间
- created_at: 创建时间
- updated_at: 更新时间
```

## API接口

### 1. 获取自定义模型列表
```
GET /api/custom-models
Authorization: Bearer <token>
```

### 2. 添加自定义模型
```
POST /api/custom-models
Content-Type: application/json
Authorization: Bearer <token>

{
  "model_name": "gpt-4",
  "model_display_name": "GPT-4",
  "api_base_url": "https://api.openai.com/v1",
  "api_key": "sk-..."
}
```

### 3. 测试模型连接
```
POST /api/custom-models/{model_id}/test
Authorization: Bearer <token>
```

### 4. 更新模型
```
PUT /api/custom-models/{model_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "model_display_name": "新名称",
  "api_base_url": "https://new-api.com/v1",
  "api_key": "new-key"
}
```

### 5. 删除模型
```
DELETE /api/custom-models/{model_id}
Authorization: Bearer <token>
```

## 安全性

1. **API密钥加密**：
   - API密钥在传输过程中使用HTTPS加密
   - 存储在数据库中（建议生产环境加密存储）
   - 列表显示时只显示部分密钥（如 `***1234`）

2. **权限控制**：
   - 用户只能管理自己的模型
   - 所有操作都需要身份验证

3. **输入验证**：
   - 所有字段都进行格式和长度验证
   - API地址必须是有效的URL
   - 防止SQL注入和XSS攻击

## 兼容的模型服务

支持任何兼容OpenAI API格式的服务，包括但不限于：
- OpenAI GPT系列
- Azure OpenAI
- Claude (通过兼容层)
- 本地部署的模型（如 LLaMA, Vicuna等，通过vLLM或text-generation-webui）
- 其他兼容服务（Anthropic, Cohere等）

## 注意事项

1. **API格式要求**：
   - 必须兼容OpenAI的 `/v1/chat/completions` 端点
   - 必须支持流式响应（stream=true）

2. **密钥安全**：
   - 不要分享你的API密钥
   - 定期更新密钥
   - 删除不使用的模型

3. **费用提醒**：
   - 使用第三方API可能产生费用
   - 请在对应平台查看使用情况和账单

4. **测试建议**：
   - 添加新模型后先进行测试
   - 定期测试确保模型可用
   - 遇到问题及时更新配置

## 故障排除

### 测试连接失败
1. 检查API地址是否正确
2. 确认API密钥有效
3. 检查网络连接
4. 确认模型名称正确
5. 查看API服务商的状态页面

### 模型无法使用
1. 重新测试连接
2. 检查API配额是否用完
3. 确认账户余额充足
4. 查看浏览器控制台错误信息

### 无法添加模型
1. 确保所有字段都已填写
2. 检查字段格式是否正确
3. 查看是否已存在同名模型
4. 检查网络连接状态

## 更新日志

### v8.1.0 (2025-01-09)
- ✨ 新增自定义AI模型功能
- ✨ 支持API连通性测试
- ✨ 模型管理界面
- ✨ 集成到主聊天界面
- 🎨 蓝色主题美化设计
- 🔒 增强安全性和权限控制

