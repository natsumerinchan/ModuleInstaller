@chcp 65001 >nul
@echo off
title 模块安装器启动器

:loop0
cls
echo ========================================
echo       模块安装器 - 设备选择
echo ========================================
echo.
adb devices
echo.
set DEVICE=
set /p DEVICE=请输入目标设备号（留空则使用默认设备）:
cls

:loop1
cls
echo ========================================
echo       模块安装器 - 模块选择
echo ========================================
echo.
echo 当前设备: %DEVICE%
echo.
cd /d %~dp0
set zipPath=
set /p zipPath=请输入模块zip路径（支持拖拽文件到此窗口）:

REM 去除路径中的引号（如果用户拖拽文件会自动添加引号）
set zipPath=%zipPath:"=%

if "%zipPath%" == "" (
    echo 错误: 模块路径不能为空！
    pause
    goto loop1
)

REM 检查文件是否存在
if not exist "%zipPath%" (
    echo 错误: 文件不存在 - %zipPath%
    pause
    goto loop1
)

echo.
echo 正在安装模块，请稍候...
echo.

if "%DEVICE%" == "" (
    python "%~dp0ModuleInstaller.py" "%zipPath%"
) else (
    python "%~dp0ModuleInstaller.py" "%zipPath%" -d %DEVICE%
)

echo.
echo ========================================
:loop2
set choose0=
set /p choose0=是否继续安装其他模块？(y/N):

if /i "%choose0%" == "y" (
    goto loop1
) else if /i "%choose0%" == "n" (
    echo 退出程序...
    timeout /t 2 >nul
    exit
) else (
    echo 请输入 y 或 n
    goto loop2
)


