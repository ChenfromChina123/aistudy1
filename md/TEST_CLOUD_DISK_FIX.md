# 云盘登录修复 - 测试指南

## 快速测试步骤

### 步骤1: 启动后端服务

```bash
cd py
python run.py
```

确保看到输出：
```
INFO:     Uvicorn running on http://[::]:5000 (Press CTRL+C to quit)
```

### 步骤2: 打开浏览器

1. 访问 `http://localhost:5000/html/index.html`
2. 完成登录流程

### 步骤3: 打开浏览器开发工具

按 `F12` 打开开发工具，切换到 **Console** 标签

### 步骤4: 导航到云盘

点击主菜单中的"云盘"或直接访问 `http://localhost:5000/html/cloud_disk.html`

### 步骤5: 观察Console输出

你应该看到以下日志输出（成功的情况）：

```
云盘初始化中... API_BASE_URL: http://localhost:5000
开始验证Token...
验证Token响应状态: 200
验证Token响应数据: {valid: true, user_id: 21, username: "...", message: "Token验证成功"}
Token验证成功，加载文件夹树
获取文件夹响应状态: 200
获取文件夹响应数据: {tree: Array(1), ...}
成功加载文件夹树，根节点: {path: "/", name: "根目录", type: "folder", ...}
```

## 问题诊断表

| 问题现象 | Console日志 | 解决方案 |
|---------|-----------|--------|
| 页面加载，但显示"登录已过期" | "未找到token，需要重新登录" | 重新登录，检查localStorage |
| 页面加载，但显示"登录已过期" | "用户信息不完整，需要重新登录" | 清空localStorage，重新登录 |
| 页面加载，但显示"登录已过期" | "Token验证异常: ..." | 查看具体错误信息，token可能已过期 |
| 通过验证，但显示空白 | "没有文件夹数据，显示空状态" | 正常现象，说明没有文件，可以上传文件 |
| 通过验证，但显示空白 | "加载文件夹失败: HTTP 403" | 权限问题，检查user_id是否匹配 |
| 页面完全无反应 | 没有任何日志 | 检查HTML文件是否正确加载，检查JavaScript是否有错误 |

## 网络请求检查

打开浏览器开发工具的 **Network** 标签，检查以下请求：

### 1. POST /api/auth/verify

**期望结果:**
- Status: `200 OK`
- Response Body:
```json
{
    "valid": true,
    "user_id": 21,
    "username": "your_username",
    "message": "Token验证成功"
}
```

**如果失败 (Status 401):**
```json
{
    "detail": "Token已过期" 或其他错误消息
}
```

### 2. GET /api/cloud_disk/files?user_id=21

**期望结果:**
- Status: `200 OK`
- Response Body 包含 `tree` 字段，例如：
```json
{
    "tree": [
        {
            "path": "/",
            "name": "根目录",
            "type": "folder",
            "children": [...]
        }
    ]
}
```

**如果失败：**
- Status 401: Token已过期
- Status 403: 无权访问
- Status 500: 服务器错误

## 修复验证检查清单

- [ ] 能访问云盘页面 (不显示登录错误)
- [ ] Console显示 "Token验证成功"
- [ ] API响应显示 HTTP 200 OK
- [ ] 能看到文件夹树结构
- [ ] 能上传文件
- [ ] 能下载文件
- [ ] 能创建新文件夹
- [ ] 能删除文件

## 后端日志检查

查看后端日志中的以下信息：

```
INFO:     ::1:65374 - "POST /api/auth/verify HTTP/1.1" 200 OK
INFO:     ::1:65374 - "GET /api/cloud_disk/files?user_id=21 HTTP/1.1" 200 OK
```

所有请求应该返回 200 OK。如果有 401 或 500 错误，说明有问题。

## 重置/恢复步骤

如果需要完全重置浏览器状态：

### 浏览器层面

```javascript
// 在浏览器Console中执行
localStorage.clear();
sessionStorage.clear();
location.reload();
```

### 重新登录

1. 刷新页面
2. 显示登录模态框
3. 输入邮箱和密码
4. 点击登录
5. 等待重定向到主页
6. 点击云盘

## 常见成功标志

✅ 云盘页面加载没有错误提示
✅ 左侧显示文件夹树 
✅ 右侧显示文件列表或空状态
✅ 可以上传文件
✅ 可以创建文件夹
✅ Console中有清晰的日志输出

## 如果仍然有问题

1. **收集信息:**
   - 浏览器版本和操作系统
   - Console中的完整错误信息
   - Network标签中失败请求的详细信息
   - 后端日志输出

2. **检查服务器地址:**
   ```javascript
   // 在Console中输入
   console.log(API_BASE_URL);  // 应该显示 http://localhost:5000
   console.log(window.location.hostname);  // 应该显示 localhost
   ```

3. **测试API连接:**
   ```bash
   # 在终端中测试
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/auth/verify
   ```

---

**文档版本**: 1.0  
**最后更新**: 2025年11月11日

