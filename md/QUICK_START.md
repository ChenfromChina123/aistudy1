# 快速开始指南 - 修复后的系统

## 🎯 5分钟快速开始

### 1. 启动后端服务

```bash
cd py/
python run.py
```

系统会输出：
```
INFO:     Uvicorn running on http://127.0.0.1:5000
```

### 2. 访问前端页面

在浏览器中打开：
```
http://localhost:5000/html/index.html
```

### 3. 开始使用

#### ✅ 翻译功能（已修复）
1. 在聊天框中输入文本
2. 点击工具栏中的 **📝 翻译** 按钮
3. 选择目标语言
4. 点击 **翻译** 按钮
5. 等待翻译结果

#### ✅ 笔记功能（已修复）
1. 点击工具栏中的 **📓 笔记** 按钮
2. 输入笔记标题和内容
3. 点击 **保存** 按钮
4. 笔记会自动保存到系统

#### ✅ 云盘管理（已修复）
1. 点击左侧菜单中的 **云盘** 选项
2. 选择文件或拖拽文件到上传区
3. 点击 **开始上传** 按钮
4. 下载时自动正确显示中文文件名

## 🔧 配置要求

### 系统要求
- Python 3.8 或更高版本
- MySQL 5.7 或更高版本
- 2GB 或更高 RAM
- 100MB 或更高硬盘空间

### 环境变量（.env文件）
```
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ipv6_education
DEEPSEEK_API_KEY=your_api_key_here
JWT_SECRET_KEY=your_secret_key_here
DOUBAO_BASEURL=https://api.doubao.com/v1
MAX_TOKEN=4096
```

## 📋 已修复的问题

| 问题 | 状态 | 文件位置 |
|------|------|--------|
| 翻译按钮无反应 | ✅ 已修复 | `html/index.html:3671-3673` |
| 笔记按钮无反应 | ✅ 已修复 | `html/index.html:3671-3673` |
| 云盘显示未登录 | ✅ 已修复 | `html/cloud_disk.html:763` |
| 中文文件名乱码 | ✅ 已修复 | `py/app.py:1744-1762, 4035-4053` |

## 🚀 生产环境部署

### 1. 服务器配置

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python py/run_migration.py

# 创建管理员账户
python py/set_admin_by_email.py
```

### 2. Nginx配置（推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /html {
        root /path/to/project;
    }
}
```

### 3. 启动服务

```bash
# 使用 Gunicorn 在后台运行
gunicorn -w 4 -b 0.0.0.0:5000 py.app:app
```

## 🧪 功能测试

### 测试翻译功能
```bash
curl -X POST http://localhost:5000/api/ask/translate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"question": "翻译 Hello World 为中文"}'
```

### 测试笔记功能
```bash
# 列出所有笔记
curl http://localhost:5000/api/notes/list \
  -H "Authorization: Bearer YOUR_TOKEN"

# 保存笔记
curl -X POST http://localhost:5000/api/notes/save \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title": "我的笔记", "content": "笔记内容"}'
```

### 测试文件下载
```bash
# 下载文件（会自动处理中文文件名）
curl http://localhost:5000/api/cloud_disk/download/1?user_id=1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o downloaded_file
```

## 📚 完整文档

- **修复总结**：查看 `FIX_SUMMARY_20251111.md`
- **部署清单**：查看 `DEPLOYMENT_CHECKLIST.md`
- **修复报告**：查看 `修复完成报告.txt`

## ⚡ 常见问题解答

### Q: 翻译功能显示"翻译中..."后没反应？
A: 检查 `DEEPSEEK_API_KEY` 是否正确配置，或查看后端日志获取详细错误信息

### Q: 云盘上传后看不到文件？
A: 刷新页面或清除浏览器缓存，确保后端服务正在运行

### Q: 下载文件时文件名显示为问号？
A: 这已经通过修复解决了，请确保使用了最新版本的代码

### Q: 笔记无法保存？
A: 检查是否已登录，确保 Bearer Token 有效

## 🔐 安全提示

1. **不要在代码中暴露敏感信息**
   - API Keys 应放在 `.env` 文件中
   - 使用环境变量管理配置

2. **定期更新依赖**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **启用HTTPS**
   - 生产环境必须使用 HTTPS
   - 配置 SSL 证书

4. **限制API调用**
   - 实施速率限制
   - 监控异常活动

## 📞 获取帮助

如遇问题，请：

1. 查看系统日志
   ```bash
   tail -f logs/system.log
   ```

2. 检查浏览器控制台（F12）
   - 查看 Console 标签获取JavaScript错误
   - 查看 Network 标签获取API调用情况

3. 查看 README.md 或相关文档

## ✅ 验证检查表

部署前请确认：

- [ ] 后端服务已启动
- [ ] 数据库连接正常
- [ ] API 密钥已配置
- [ ] 前端页面可访问
- [ ] 翻译功能正常
- [ ] 笔记功能正常
- [ ] 云盘管理可用
- [ ] 文件上传/下载正常
- [ ] 中文文件名显示正确
- [ ] 生产环境安全配置完成

## 🎉 享受使用！

所有功能现已修复并可用。祝您使用愉快！

有任何问题或建议，欢迎反馈。

---

**修复日期**：2025年11月11日
**系统版本**：4.0+
**最后更新**：2025年11月11日

