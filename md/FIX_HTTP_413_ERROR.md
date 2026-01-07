# 修复 HTTP 413 错误（文件上传大小限制）

## 问题描述
上传大文件（如视频文件）时出现 HTTP 413 Payload Too Large 错误。

## 已完成的修复

### 1. 后端配置
- ✅ 将 `MAX_FILE_SIZE` 从 100MB 增加到 **500MB**（默认值）
- ✅ 支持通过环境变量 `MAX_FILE_SIZE` 自定义配置
- ✅ 添加了请求体大小检查中间件
- ✅ 更新了 Uvicorn 配置以支持大文件上传

### 2. 环境变量配置
在 `py/env` 文件中已添加：
```bash
export MAX_FILE_SIZE='524288000'  # 500MB
```

## 需要执行的步骤

### 步骤 1: 重启服务器
**重要**：修改配置后必须重启服务器才能生效！

```bash
# 停止当前运行的服务器
# 然后重新启动
cd /www/project/基于IPv6的AI智能学习伴侣导师8.1/py
python run.py
```

### 步骤 2: 检查 Nginx 配置（如果使用 Nginx 反向代理）

如果您的服务器前面有 Nginx 反向代理，需要修改 Nginx 配置：

```bash
# 编辑 Nginx 配置文件
sudo vi /etc/nginx/nginx.conf
# 或
sudo vi /etc/nginx/sites-available/your-site
```

在 `http`、`server` 或 `location` 块中添加：

```nginx
client_max_body_size 1G;  # 或更大的值，如 2G
```

然后重启 Nginx：
```bash
sudo nginx -t  # 测试配置
sudo systemctl restart nginx  # 重启 Nginx
```

### 步骤 3: 验证配置

重启服务器后，查看日志应该显示：
```
最大文件大小限制: 500MB (可通过环境变量 MAX_FILE_SIZE 配置)
```

### 步骤 4: 如果需要更大的文件限制

如果 500MB 还不够，可以在环境文件中设置更大的值：

```bash
# 1GB = 1073741824 字节
export MAX_FILE_SIZE='1073741824'  # 1GB

# 2GB = 2147483648 字节
export MAX_FILE_SIZE='2147483648'  # 2GB
```

**注意**：同时需要更新 Nginx 的 `client_max_body_size` 配置。

## 常见问题

### Q: 为什么还是出现 413 错误？
A: 可能的原因：
1. 服务器没有重启，配置未生效
2. Nginx 的 `client_max_body_size` 限制太小
3. 文件实际大小超过了配置的限制

### Q: 如何检查文件大小？
A: 在浏览器控制台可以看到文件大小信息，或使用：
```bash
ls -lh /path/to/file
```

### Q: 如何查看当前配置的限制？
A: 查看服务器启动日志，应该显示：
```
最大文件大小限制: 500MB (可通过环境变量 MAX_FILE_SIZE 配置)
```

## 验证修复

1. 重启服务器
2. 检查日志确认配置已加载
3. 尝试上传文件
4. 如果仍然失败，检查 Nginx 配置

## 技术说明

- FastAPI/Starlette 默认的请求体大小限制是 1MB
- 我们的中间件会在请求到达路由之前检查 Content-Length
- 实际的文件大小检查在路由处理函数中进行
- Nginx 的 `client_max_body_size` 默认是 1MB，需要手动配置

