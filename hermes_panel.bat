@echo off
chcp 65001 >nul
cd /d "%~dp0"
.venv\Scripts\activate
python hermes_control.py
