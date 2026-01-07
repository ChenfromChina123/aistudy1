# 数据库迁移脚本 - 依赖说明

## 📦 必需依赖

### 1. 安装依赖

在项目根目录或 `py/script/数据库迁移/` 目录下运行：

```bash
pip install -r py/script/数据库迁移/requirements.txt
```

### 2. 依赖列表

| 依赖包 | 版本 | 说明 |
|--------|------|------|
| sqlalchemy | >=1.4.0 | 数据库ORM框架 |
| pymysql | >=1.0.0 | MySQL数据库驱动 |
| python-dotenv | >=0.19.0 | 环境变量管理（读取.env文件） |

### 3. 快速安装命令

```bash
# Windows
pip install sqlalchemy pymysql python-dotenv

# Linux/Mac
pip3 install sqlalchemy pymysql python-dotenv
```

## 🔧 特殊说明

### 文件夹路径选择

脚本已改为命令行输入路径方式，**不再需要图形界面**，适合服务器环境使用。

- 可以直接使用默认路径（直接回车）
- 也可以手动输入文件夹路径
- 支持相对路径和绝对路径

## ✅ 验证安装

运行以下命令验证依赖是否安装成功：

```bash
python -c "import sqlalchemy; import pymysql; import dotenv; print('所有依赖已安装')"
```

## 🚀 使用

安装完依赖后，直接运行：

```bash
python py/script/数据库迁移/简单迁移.py
```

或双击 `运行迁移.bat`（Windows）

