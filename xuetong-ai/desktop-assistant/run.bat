@echo off
chcp 65001 >nul
title AI 桌面助手
cd /d "%~dp0"
echo 正在启动...
python desktop-ai.py
pause
