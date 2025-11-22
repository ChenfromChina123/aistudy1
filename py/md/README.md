# 基于IPv6的AI智能学习伴侣导师

一个支持IPv6的AI智能学习助手系统，提供聊天、文件管理、学习资源推荐等功能。

## 功能特性

- **AI聊天功能**：支持创建聊天会话、发送消息、获取聊天历史
- **文件管理**：支持文件上传、下载、分享
- **用户反馈**：支持用户提交反馈，管理员回复
- **IPv6支持**：完全兼容IPv6网络环境
- **RESTful API**：提供标准的API接口
- **WebSocket实时通信**：支持实时聊天功能

## 技术栈

- **后端框架**：FastAPI
- **数据库**：SQLAlchemy（ORM）
- **认证**：JWT
- **WebSocket**：支持实时通信
- **异步支持**：基于Python asyncio

## 项目结构

```
py/
├── app.py              # FastAPI应用主文件
├── run.py              # 应用启动入口
├── config.py           # 配置管理
├── database.py         # 数据库连接配置
├── routers/            # 路由模块
│   ├── __init__.py
│   ├── chat.py         # 聊天相关路由
│   ├── file.py         # 文件相关路由
│   └── feedback.py     # 反馈相关路由
├── services/           # 业务逻辑层
│   ├── __init__.py
│   ├── chat_service.py
│   ├── file_service.py
│   └── feedback_service.py
├── models/             # 数据库模型
│   └── __init__.py
├── schemas/            # 数据传输对象
│   ├── __init__.py
│   ├── chat.py
│   ├── file.py
│   ├── feedback.py
│   └── response.py
├── static/             # 静态文件目录
├── uploads/            # 文件上传目录
└── requirements.txt    # 依赖列表
```

## 安装和运行

### 1. 安装依赖

```bash
cd py
pip install -r requirements.txt
```

### 2. 配置环境变量

创建`.env`文件：

```
# 数据库连接信息
DATABASE_URL="sqlite:///./app.db"

# JWT密钥
SECRET_KEY="your-secret-key-here"

# 应用配置
HOST="::"  # 支持IPv6
PORT=5000
DEBUG=True

# 文件存储配置
UPLOAD_DIR="./uploads"
MAX_FILE_SIZE=52428800  # 50MB
```

### 3. 启动应用

```bash
python run.py
```

应用将在以下地址运行：
- API文档：http://[::1]:5000/docs
- API地址：http://[::1]:5000/api

## API接口文档

启动应用后，可以通过访问`http://[::1]:5000/docs`查看完整的API文档。

### 主要接口

#### 聊天相关
- `POST /api/chat/sessions` - 创建聊天会话
- `GET /api/chat/sessions` - 获取会话列表
- `GET /api/chat/sessions/{session_id}` - 获取会话详情
- `PUT /api/chat/sessions/{session_id}` - 更新会话
- `DELETE /api/chat/sessions/{session_id}` - 删除会话
- `POST /api/chat/sessions/{session_id}/messages` - 发送消息
- `GET /api/chat/sessions/{session_id}/messages` - 获取聊天记录
- `DELETE /api/chat/sessions/{session_id}/messages` - 清空聊天记录
- `POST /api/chat/quick` - 快速聊天
- `WebSocket /ws/chat/{session_id}` - 实时聊天WebSocket

#### 文件相关
- `POST /api/files/upload` - 上传文件
- `GET /api/files` - 获取文件列表
- `GET /api/files/{file_id}` - 获取文件信息
- `PUT /api/files/{file_id}` - 更新文件信息
- `DELETE /api/files/{file_id}` - 删除文件
- `GET /api/files/{file_id}/download` - 下载文件
- `POST /api/files/{file_id}/share` - 分享文件
- `GET /api/files/share/{share_token}` - 获取分享文件
- `GET /api/files/share/{share_token}/verify` - 验证分享链接

#### 反馈相关
- `POST /api/feedback` - 提交反馈
- `GET /api/feedback` - 获取用户反馈列表
- `GET /api/feedback/{feedback_id}` - 获取反馈详情
- `PUT /api/feedback/{feedback_id}` - 更新反馈
- `DELETE /api/feedback/{feedback_id}` - 删除反馈
- `PUT /api/feedback/{feedback_id}/read` - 标记为已读

## 开发注意事项

1. 确保Python版本 >= 3.10
2. 开发时设置DEBUG=True以启用热重载
3. 生产环境请使用正确的数据库配置和密钥
4. 确保服务器支持IPv6网络

## 许可证

MIT License