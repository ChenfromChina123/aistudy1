@echo off
chcp 65001 >nul
cd /d "%~dp0\..\..\.."
python py\script\数据库迁移\简单迁移.py
pause

