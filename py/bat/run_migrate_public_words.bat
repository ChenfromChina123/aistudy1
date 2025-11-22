@echo off
chcp 65001 >nul
echo ========================================
echo 公共单词迁移工具
echo ========================================
echo.
echo 正在启动迁移脚本...
echo.

cd /d "%~dp0"
python migrate_public_words.py

echo.
echo 按任意键退出...
pause >nul





