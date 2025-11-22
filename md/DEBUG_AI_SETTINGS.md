# AI设置保存调试指南

## 问题诊断步骤

### 1. 打开浏览器开发者工具
按 `F12` 或 右键 > 检查，打开浏览器控制台。

### 2. 点击"保存AI设置"按钮后，查看控制台输出

在控制台中应该看到以下日志信息：

```
开始保存AI设置...
发送的设置数据: {model_name: "...", api_base: "...", model_params: "..."}
API响应状态: 200 OK
API返回的数据: {id: ..., user_id: ..., model_name: "..."}
```

### 3. 检查后端日志

在服务器终端中应该看到类似的日志：

```
[INFO] 用户 {user_id} 尝试保存AI设置
[DEBUG] 收到的设置数据: UserSettingsCreate(model_name='...', api_base='...', ...)
[DEBUG] 实际设置的字段 (exclude_unset=True): ['model_name', 'api_base', ...]
[INFO] 用户 {user_id} 的AI设置已保存: model_name=..., has_api_key=True, updated_fields=[...]
```

## 常见问题与解决方案

### 问题1：点击保存按钮没有反应

**原因**：Token 过期或浏览器 localStorage 中没有 token

**解决方案**：
1. 重新刷新页面
2. 重新登录
3. 检查浏览器开发工具 > Application > LocalStorage > access_token 是否存在

### 问题2：看到"模型参数JSON格式错误"

**原因**：`modelParams` 字段的 JSON 格式不正确

**解决方案**：
1. 检查滑块是否正确更新了隐藏字段
2. 在控制台输入以检查 JSON：
```javascript
JSON.parse(document.getElementById('modelParams').value)
```

### 问题3：API返回 500 错误

**原因**：后端数据库保存出错

**解决方案**：
1. 检查服务器日志中的详细错误信息
2. 确保数据库连接正常
3. 检查用户ID是否有效

### 问题4：保存成功但刷新后设置消失

**原因**：
1. 设置没有真正保存到数据库
2. 加载设置时出错

**解决方案**：
1. 检查数据库中是否有 `user_settings` 表的数据
```sql
SELECT * FROM user_settings WHERE user_id = {user_id};
```
2. 检查 `loadAISettings()` 函数的日志输出

## 调试命令

### 在浏览器控制台手动测试保存

```javascript
// 1. 检查 token
localStorage.getItem('access_token')

// 2. 手动调用保存函数
saveAISettings()

// 3. 检查设置是否被加载
loadAISettings()

// 4. 查看隐藏字段的值
document.getElementById('modelParams').value
document.getElementById('modelName').value
document.getElementById('apiBase').value
```

### 在服务器终端查看详细日志

```bash
# 如果使用了 logging 模块，查看日志输出
# 日志级别应该是 DEBUG 或 INFO
```

## 预期行为

1. 用户修改任何参数
2. 点击"保存AI设置"按钮
3. 显示"AI设置保存成功"提示信息
4. 刷新页面后，设置应该保持不变
5. 调用 AI API 时应该使用保存的参数

## 数据流图

```
用户修改参数 
    ↓
点击"保存AI设置"
    ↓
前端: saveAISettings() 
    ↓
发送 POST /api/settings 请求
    ↓
后端: update_user_settings()
    ↓
更新数据库中的 user_settings 表
    ↓
返回更新后的设置给前端
    ↓
前端: loadAISettings() 重新加载设置
    ↓
显示"保存成功"提示
```

## 关键要点

- ✅ `model_params` 必须是有效的 JSON 字符串
- ✅ API 密钥使用掩码显示，保存时如果是掩码则不覆盖现有值
- ✅ 后端使用 `exclude_unset=True` 只更新提供的字段
- ✅ 保存后自动重新加载设置以确保显示最新值



