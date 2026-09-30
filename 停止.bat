@echo off
title 停止服务

echo.
echo   正在停止人岗匹配评估系统的服务 ...
echo.

call :kill 8000 后端 (FastAPI)
call :kill 3000 前端 (Vite)

echo.
echo   完成。可以直接关闭本窗口。
echo.
pause
exit /b 0

:kill
set "found="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%~1 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>nul
    if not errorlevel 1 (
        echo   [OK] 已停止 %~2   PID %%p
        set "found=1"
    )
)
if not defined found echo   [--] %~2 未在运行
exit /b 0
