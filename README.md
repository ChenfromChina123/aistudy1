# 基于IPv6的AI智能学习伴侣导师

<div align="center">

![Version](https://img.shields.io/badge/version-8.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a09d.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**一个基于FastAPI和IPv6的智能学习助手系统**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [API文档](#-api文档) • [项目结构](#-项目结构)

</div>

---

## 📋 目录

- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
  - [配置说明](#配置说明)
  - [运行应用](#运行应用)
- [API文档](#-api文档)
- [项目结构](#-项目结构)
- [核心功能](#-核心功能)
- [开发指南](#-开发指南)
- [部署指南](#-部署指南)
- [常见问题](#-常见问题)
- [更新日志](#-更新日志)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## ✨ 功能特性

### 核心功能

- 🔐 **用户认证系统**
  - 邮箱注册/登录
  - JWT Token认证
  - 密码找回功能
  - 账户管理

- 🤖 **AI智能问答**
  - 集成DeepSeek和豆包AI模型
  - 流式回答输出
  - 多模型支持
  - 上下文记忆

- 📝 **聊天记录管理**
  - 会话创建和管理
  - 历史消息查看
  - 会话删除
  - 消息状态跟踪

- 📚 **学习资源管理**
  - 资源分类管理
  - 资源添加/删除
  - 收藏功能
  - 资源搜索

- 📁 **云盘功能**
  - 文件上传/下载
  - 多格式支持（文档、图片、视频等）
  - 视频自动压缩
  - 文件管理

- 📖 **语言学习**
  - 单词表管理
  - 学习进度跟踪
  - 单词复习
  - AI生成学习文章

- 👨‍💼 **管理后台**
  - 用户管理
  - 文件管理
  - 反馈处理
  - 系统监控

- 🌐 **IPv6支持**
  - 原生IPv6网络支持
  - IPv6连接测试
  - 双栈网络兼容

---

## 🛠️ 技术栈

### 后端

- **框架**: FastAPI 0.104+
- **数据库**: MySQL (SQLAlchemy ORM)
- **认证**: JWT (python-jose)
- **密码加密**: Passlib (bcrypt)
- **AI服务**: OpenAI兼容API (DeepSeek, 豆包)
- **服务器**: Uvicorn (ASGI)

### 前端

- **技术**: HTML5 + CSS3 + JavaScript (原生)
- **UI特性**: 响应式设计、深色模式支持
- **交互**: 流式AI回答、实时文件上传

### 基础设施

- **网络**: IPv6/IPv4双栈支持
- **文件存储**: 本地文件系统
- **邮件服务**: SMTP (QQ邮箱)

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MariaDB 10.3+
- IPv6网络支持（可选）

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd 基于IPv6的AI智能学习伴侣导师8.1
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或者使用虚拟环境（推荐）：

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. 配置数据库

创建MySQL数据库：

```sql
CREATE DATABASE IF NOT EXISTS ipv6_education
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

#### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost/ipv6_education

# JWT密钥（请使用强密钥）
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# AI模型API密钥
DEEPSEEK_API_KEY=your-deepseek-api-key
DOUBAO_KEY=your-doubao-api-key
DOUBAO_BASEURL=https://api.doubao.com/v1

# 其他配置
MAX_TOKEN=4096
```

### 配置说明

#### 数据库配置

- **DATABASE_URL**: MySQL连接字符串
  - 格式: `mysql+pymysql://用户名:密码@主机:端口/数据库名`
  - 示例: `mysql+pymysql://root:123456@localhost:3306/ipv6_education`

#### AI模型配置

- **DEEPSEEK_API_KEY**: DeepSeek API密钥
  - 获取地址: https://platform.deepseek.com
- **DOUBAO_KEY**: 豆包API密钥
- **DOUBAO_BASEURL**: 豆包API基础URL

#### JWT配置

- **JWT_SECRET_KEY**: JWT签名密钥
  - ⚠️ **重要**: 生产环境必须使用强密钥（至少32字符）
  - 建议使用随机生成的密钥

### 运行应用

#### 开发模式

```bash
cd py
python run.py
```

或者使用uvicorn直接运行：

```bash
cd py
uvicorn app:app --host :: --port 5000 --reload
```

#### 生产模式

```bash
cd py
uvicorn app:app --host :: --port 5000 --workers 4
```

访问地址：
- IPv6: http://[::]:5000
- IPv4: http://localhost:5000
- 本地IPv6: http://[::1]:5000
- API文档: http://localhost:5000/docs
- ReDoc文档: http://localhost:5000/redoc

> 💡 **提示**: 详细的启动指南请参考 [START_GUIDE.md](./START_GUIDE.md)

---

## 📖 API文档

### 自动生成的文档

FastAPI自动生成了交互式API文档：

- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

### 主要API端点

#### 认证相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/register/email` | POST | 发送注册验证码 |
| `/api/register` | POST | 用户注册 |
| `/api/login` | POST | 用户登录 |
| `/api/forgot-password/email` | POST | 发送重置密码验证码 |
| `/api/forgot-password` | POST | 重置密码 |
| `/api/delete-account` | DELETE | 删除账户 |

#### AI问答

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ask-stream` | POST | 流式AI问答 |

#### 聊天记录

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat-records/save` | POST | 保存聊天记录 |
| `/api/chat-records/sessions` | GET | 获取会话列表 |
| `/api/chat-records/session/{session_id}` | GET | 获取会话消息 |
| `/api/chat-records/new-session` | POST | 创建新会话 |

#### 文件管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/cloud_disk/upload` | POST | 上传文件 |
| `/api/cloud_disk/files` | GET | 获取文件列表 |
| `/api/cloud_disk/download/{file_id}` | GET | 下载文件 |
| `/api/cloud_disk/delete/{file_id}` | DELETE | 删除文件 |

详细API文档请参考：
- [完整API文档](./api_documentation.md)
- [语言学习API文档](./api_documentation_language_learning.md)

---

## 📁 项目结构

```
项目根目录/
├── py/                          # Python后端代码
│   ├── app.py                   # FastAPI主应用
│   ├── run.py                   # 应用启动文件
│   ├── language_learning.py     # 语言学习模块
│   ├── chat_records.py          # 聊天记录模块
│   ├── jwt加密.py               # JWT工具（待重命名）
│   ├── 自动邮箱.py              # 邮件工具（待重命名）
│   ├── cloud_disk/              # 云盘文件存储
│   └── uploads/                 # 上传文件存储
├── html/                        # 前端HTML文件
│   ├── index.html               # 主页面
│   ├── admin.html               # 管理页面
│   ├── language_learning.html   # 语言学习页面
│   ├── cloud_disk.html          # 云盘页面
│   ├── chat_management.html     # 聊天管理页面
│   └── css/                     # CSS样式文件（待提取）
├── 数据库/                      # 数据库相关文件
├── cloud_disk/                  # 云盘存储目录
├── uploads/                     # 文件上传目录
├── instance/                    # SQLite数据库（备用）
├── fastapi_requirements.txt     # Python依赖
├── README.md                    # 本文件
├── README_FASTAPI.md            # FastAPI详细说明
├── api_documentation.md         # API文档
├── api_documentation_language_learning.md  # 语言学习API文档
├── file_processing_standards.md # 文件处理标准
└── PROJECT_ANALYSIS_AND_OPTIMIZATION.md  # 项目分析与优化方案
```

---

## 🎯 核心功能

### 用户认证流程

1. 用户注册 → 发送验证码 → 验证邮箱 → 创建账户
2. 用户登录 → JWT Token生成 → Token存储 → 后续请求携带Token
3. 密码找回 → 发送验证码 → 验证码验证 → 重置密码

### AI问答流程

1. 用户提问 → 创建会话 → 调用AI API → 流式返回结果
2. 保存消息 → 存储到数据库 → 更新会话信息

### 文件管理流程

1. 文件上传 → 验证类型/大小 → 生成唯一文件名 → 保存到云盘
2. 视频文件 → 自动压缩为ZIP → 保存
3. 文件下载 → 验证权限 → 返回文件流

---

## 👨‍💻 开发指南

### 代码规范

- 使用Python 3.8+语法
- 遵循PEP 8编码规范
- 使用类型提示（Type Hints）
- 添加必要的注释和文档字符串

### 项目优化计划

本项目正在进行系统化优化，详细计划请参考：
[项目分析与优化方案](./PROJECT_ANALYSIS_AND_OPTIMIZATION.md)

### 添加新功能

1. 在 `py/models/` 中定义数据库模型
2. 在 `py/schemas/` 中定义Pydantic模型
3. 在 `py/routers/` 中添加路由
4. 在 `py/services/` 中实现业务逻辑
5. 更新API文档

---

## 🚢 部署指南

### 生产环境配置

1. **环境变量**
   - 使用强JWT密钥
   - 配置正确的数据库连接
   - 设置AI API密钥

2. **服务器配置**
   - 使用Nginx作为反向代理
   - 配置HTTPS
   - 设置文件上传大小限制

3. **数据库优化**
   - 创建必要的索引
   - 配置连接池
   - 定期备份

4. **文件存储**
   - 确保足够的存储空间
   - 设置正确的文件权限
   - 考虑使用对象存储服务

详细部署说明请参考 [部署文档](./docs/DEPLOYMENT.md)

---

## ❓ 常见问题

### Q: 服务器无法启动？

**A**: 检查以下几点：
- 端口5000是否被占用
- 环境变量是否正确配置
- 数据库连接是否正常
- 依赖是否完整安装

### Q: IPv6测试失败？

**A**: 
- 确保网络环境支持IPv6
- 检查防火墙配置
- 可以修改配置使用IPv4

### Q: AI模型调用失败？

**A**: 
- 检查API密钥是否正确
- 确认网络连接正常
- 查看日志文件了解详细错误

### Q: 文件上传失败？

**A**: 
- 确保已安装 `python-multipart`
- 检查文件大小是否超过限制（100MB）
- 确认文件类型在允许列表中
- 检查文件存储目录权限

### Q: 邮件发送失败？

**A**: 
- 检查SMTP配置是否正确
- 确认QQ邮箱授权码有效
- 检查网络连接和防火墙设置

---

## 📝 更新日志

### Version 8.1

- ✨ 新增语言学习模块
- ✨ 优化AI问答体验
- ✨ 改进文件管理功能
- 🐛 修复多个已知问题
- 📚 完善API文档

### Version 8.0

- 🎉 从Flask迁移到FastAPI
- ✨ 新增云盘功能
- ✨ 改进用户认证系统
- 📚 新增API自动文档

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

---

## 📮 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

<div align="center">

**Made with ❤️ by the Development Team**

[⬆ 回到顶部](#-基于ipv6的ai智能学习伴侣导师)

</div>

