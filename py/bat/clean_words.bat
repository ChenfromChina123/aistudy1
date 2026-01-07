@echo off
chcp 65001 >nul
echo ============================================================
echo 公共词库数据清理工具
echo ============================================================
echo.
echo 请选择操作:
echo.
echo [1] 查看统计信息（不执行清理）
echo [2] 交互式清理（推荐）
echo [3] 强制清理（不询问确认）
echo [4] 退出
echo.
set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" (
    echo.
    echo 正在查看统计信息...
    python clean_public_words_standalone.py --stats
    goto end
)

if "%choice%"=="2" (
    echo.
    echo 开始交互式清理...
    python clean_public_words_standalone.py
    goto end
)

if "%choice%"=="3" (
    echo.
    echo ⚠️ 警告: 此操作将直接删除不规范记录，不会询问确认！
    set /p confirm=确认执行强制清理? (yes/no): 
    if /i "%confirm%"=="yes" (
        python clean_public_words_standalone.py --force
    ) else (
        echo 操作已取消
    )
    goto end
)

if "%choice%"=="4" (
    echo 退出程序
    exit /b 0
)

echo 无效的选项，请重新运行脚本

:end
echo.
echo ============================================================
echo 操作完成
echo ============================================================
pause

