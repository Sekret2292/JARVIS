@echo off
chcp 65001 >nul
title JARVIS Telegram Bot
cd /d D:\JARVIS
D:\JARVIS\.venv\Scripts\python.exe telegram_bridge.py
pause
