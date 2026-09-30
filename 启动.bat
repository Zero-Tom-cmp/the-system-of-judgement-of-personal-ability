@echo off
title 人岗匹配评估系统

set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"
set "PY=C:\Users\36003\anaconda3\python.exe"

rem 用绝对路径调用系统工具，避免被 Git/MSYS 下的同名程序抢占
set "SYS=%SystemRoot%\System32"

echo.
echo   ==========================================
echo      人岗匹配评估系统  ·  启动器
echo   ==========================================
echo.

rem ---------- 检查 Python ----------
if not exist "%PY%" (
    echo   [X] 找不到 Python：
    echo       %PY%
    echo       请修改本脚本里的 PY 变量
    echo.
    pause
    exit /b 1
)

rem ---------- 检查 Node ----------
where node >nul 2>nul
if not errorlevel 1 goto node_ok
if exist "D:\hclaw\node\node.exe" (
    set "PATH=D:\hclaw\node;%PATH%"
    echo   [!] node 不在 PATH，本次已临时启用 D:\hclaw\node
    goto node_ok
)
echo   [X] 找不到 node，请安装 Node.js 或修改本脚本
echo.
pause
exit /b 1
:node_ok

rem ---------- 启动后端 ----------
echo   [1/3] 启动后端   http://127.0.0.1:8000
start "后端 - FastAPI" /D "%PROJ%\backend" cmd /k ""%PY%" main.py"

rem ---------- 启动前端 ----------
echo   [2/3] 启动前端   http://localhost:3000
start "前端 - Vite" /D "%PROJ%\frontend" cmd /k "npm run dev"

rem ---------- 等待就绪 ----------
rem 用 ping 而非 timeout 做延时：timeout 依赖真实控制台输入，
rem stdin 一旦被重定向就会报错退出，使等待循环变成无延迟空转。
echo   [3/3] 等待服务就绪 ...
set /a n=0
:wait
set /a n+=1
"%SYS%\curl.exe" -s -o nul -m 2 http://127.0.0.1:3000 >nul 2>nul
if not errorlevel 1 goto ready
if %n% geq 40 goto slow
ping -n 2 127.0.0.1 >nul 2>nul
goto wait

:slow
echo.
echo   [!] 前端启动较慢，请手动打开 http://localhost:3000
goto done

:ready
echo.
echo   [OK] 服务已就绪，正在打开浏览器 ...
start "" http://localhost:3000

:done
echo.
echo   ------------------------------------------
echo    关闭本窗口不会停止服务。
echo    要停止服务，请运行「停止.bat」。
echo   ------------------------------------------
echo.
pause
