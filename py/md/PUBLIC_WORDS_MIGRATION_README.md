# 公共单词迁移工具使用说明

## 概述

这个工具用于将当前数据库中的公共单词迁移到服务器，包括重复检查、数据导出和服务器上传功能。

## 文件说明

- `migrate_public_words.py` - 主要的迁移脚本
- `run_migrate_public_words.bat` - Windows批处理启动脚本
- `run_migrate_public_words.sh` - Linux/Mac启动脚本

## 功能特性

1. **数据导出**: 从本地数据库导出所有公共单词
2. **重复检查**: 自动检测重复的单词记录（基于单词+语言）
3. **多格式保存**: 
   - CSV格式的txt文件（便于Excel打开）
   - JSON格式（便于程序处理）
   - 重复项报告（便于人工审核）
4. **服务器上传**: 支持直接上传到服务器API
5. **迁移脚本生成**: 自动生成服务器端的导入脚本

## 使用方法

### 方法1: 直接运行脚本

```bash
# Windows
python migrate_public_words.py

# Linux/Mac
python3 migrate_public_words.py
```

### 方法2: 使用批处理脚本

```bash
# Windows
run_migrate_public_words.bat

# Linux/Mac
chmod +x run_migrate_public_words.sh
./run_migrate_public_words.sh
```

## 环境要求

### Python依赖

```bash
pip install pymysql requests python-dotenv
```

### 环境变量配置

在项目根目录创建 `.env` 文件或设置环境变量：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名
```

示例：
```env
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/ipv6_education
```

## 输出文件

运行后会在 `exports/` 目录下生成以下文件：

1. **public_words_unique_YYYYMMDD_HHMMSS.txt**
   - CSV格式的唯一单词数据
   - 可用Excel或文本编辑器打开
   - 包含所有字段：id, word, language, definition等

2. **public_words_duplicates_YYYYMMDD_HHMMSS.txt**
   - 重复单词检测报告
   - 列出所有重复项及其详细信息
   - 便于人工审核和处理

3. **public_words_data_YYYYMMDD_HHMMSS.json**
   - JSON格式的完整数据
   - 包含单词数据和重复项信息
   - 用于程序处理和服务器导入

4. **server_migration_script_YYYYMMDD_HHMMSS.py**
   - 服务器端导入脚本
   - 包含完整的导入逻辑
   - 支持重复项处理（更新而非插入）

## 服务器部署步骤

### 1. 文件传输

将以下文件复制到服务器：
- `public_words_data_YYYYMMDD_HHMMSS.json`
- `server_migration_script_YYYYMMDD_HHMMSS.py`

### 2. 配置服务器环境变量

确保服务器上有 `.env` 文件，包含正确的数据库配置：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名
```

示例：
```env
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/ipv6_education
```

**注意**: 生成的服务器脚本会自动从环境变量读取数据库配置，无需手动修改代码。

### 3. 运行导入脚本

```bash
python3 server_migration_script_YYYYMMDD_HHMMSS.py
```

## 重复项处理策略

当检测到重复单词时，脚本采用以下策略：

1. **检测标准**: 相同的单词文本 + 语言代码
2. **保留策略**: 保留第一个遇到的记录
3. **报告生成**: 生成详细的重复项报告
4. **服务器导入**: 使用 `ON DUPLICATE KEY UPDATE` 策略
   - 如果单词已存在，更新定义、词性等信息
   - 累加使用次数
   - 更新时间戳

## 数据验证

脚本会进行以下验证：

1. **数据库连接**: 验证数据库连接是否成功
2. **数据完整性**: 检查必要字段是否存在
3. **字符编码**: 确保UTF-8编码正确处理
4. **文件生成**: 验证所有输出文件是否成功创建

## 错误处理

- **数据库连接失败**: 检查连接参数和网络
- **权限不足**: 确保数据库用户有读取权限
- **文件写入失败**: 检查磁盘空间和写入权限
- **网络上传失败**: 检查服务器地址和API密钥

## 注意事项

1. **备份数据**: 在迁移前请备份原始数据库
2. **测试环境**: 建议先在测试环境验证脚本
3. **大数据量**: 对于大量数据，考虑分批处理
4. **网络稳定**: 上传大文件时确保网络稳定
5. **权限检查**: 确保有足够的数据库和文件系统权限

## 故障排除

### 常见问题

1. **ModuleNotFoundError: No module named 'pymysql'**
   ```bash
   pip install pymysql
   ```

2. **数据库连接被拒绝**
   - 检查数据库服务是否运行
   - 验证连接参数是否正确
   - 确认防火墙设置

3. **编码错误**
   - 确保数据库使用UTF-8编码
   - 检查Python环境的编码设置

4. **文件权限错误**
   - 检查exports目录的写入权限
   - 在Linux/Mac上可能需要chmod命令

### 日志信息

脚本会输出详细的执行日志：
- `[INFO]` - 一般信息
- `[OK]` - 成功操作
- `[WARNING]` - 警告信息
- `[ERROR]` - 错误信息
- `[DUPLICATE]` - 重复项检测

## 联系支持

如果遇到问题，请提供：
1. 完整的错误信息
2. 数据库配置（隐藏敏感信息）
3. Python版本和操作系统信息
4. 执行日志

---

**版本**: 1.0  
**更新时间**: 2024-11-11  
**兼容性**: Python 3.6+, MySQL 5.7+
