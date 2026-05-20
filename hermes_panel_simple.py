#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hermes_panel.py - Панель управления Hermes Agent
Максимально просто - без классов и методов.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import psutil
import time
from pathlib import Path

# Константы
WORK_DIR = Path(__file__).parent.resolve()
HERMES_LAUNCH_SCRIPT = "herLayStart.py"
HERMES_GATEWAY_CMD = "gateway/run.py"
PORT_DASHBOARD = 8765

# Глобальные переменные для кнопок
hermes_start_btn = None
hermes_stop_btn = None
hermes_status = None
gateway_start_btn = None
gateway_stop_btn = None
gateway_status = None
dashboard_start_btn = None
dashboard_stop_btn = None
dashboard_status = None
log_widget = None

def start_hermes():
    """Запустить Hermes через herLayStart.py"""
    full_cmd = f'start "Hermes" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python {HERMES_LAUNCH_SCRIPT}"'
    subprocess.Popen(full_cmd, shell=True, cwd=str(WORK_DIR))
    log_widget.insert(tk.END, f"✓ Hermes запущен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    hermes_start_btn.config(state=tk.DISABLED)
    hermes_stop_btn.config(state=tk.NORMAL)
    hermes_status.config(text="● Запущен", foreground="green")

def stop_hermes():
    """Остановить Hermes"""
    kill_process(HERMES_LAUNCH_SCRIPT)
    log_widget.insert(tk.END, f"✓ Hermes остановлен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    hermes_start_btn.config(state=tk.NORMAL)
    hermes_stop_btn.config(state=tk.DISABLED)
    hermes_status.config(text="● Остановлен", foreground="red")

def start_gateway():
    """Запустить Gateway"""
    full_cmd = f'start "Gateway" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python -m hermes_cli.gateway.run start"'
    subprocess.Popen(full_cmd, shell=True, cwd=str(WORK_DIR))
    log_widget.insert(tk.END, f"✓ Gateway запущен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    gateway_start_btn.config(state=tk.DISABLED)
    gateway_stop_btn.config(state=tk.NORMAL)
    gateway_status.config(text="● Запущен", foreground="green")

def stop_gateway():
    """Остановить Gateway"""
    kill_process(HERMES_GATEWAY_CMD)
    log_widget.insert(tk.END, f"✓ Gateway остановлен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    gateway_start_btn.config(state=tk.NORMAL)
    gateway_stop_btn.config(state=tk.DISABLED)
    gateway_status.config(text="● Остановлен", foreground="red")

def start_dashboard():
    """Запустить Dashboard"""
    full_cmd = f'start "Dashboard" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python -m hermes dashboard"'
    subprocess.Popen(full_cmd, shell=True, cwd=str(WORK_DIR))
    log_widget.insert(tk.END, f"✓ Dashboard запущен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    dashboard_start_btn.config(state=tk.DISABLED)
    dashboard_stop_btn.config(state=tk.NORMAL)
    dashboard_status.config(text="● Запущен", foreground="green")

def stop_dashboard():
    """Остановить Dashboard"""
    kill_by_port(PORT_DASHBOARD)
    log_widget.insert(tk.END, f"✓ Dashboard остановлен\n")
    log_widget.see(tk.END)
    # Переключаем кнопки
    dashboard_start_btn.config(state=tk.NORMAL)
    dashboard_stop_btn.config(state=tk.DISABLED)
    dashboard_status.config(text="● Остановлен", foreground="red")

def kill_process(cmd_pattern):
    """Убить процесс по имени скрипта"""
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and 'python' in ' '.join(cmdline).lower():
                if cmd_pattern in ' '.join(cmdline):
                    proc.kill()
        except:
            pass

def kill_by_port(port):
    """Убить процесс на порту"""
    for proc in psutil.process_iter(['connections']):
        try:
            connections = proc.info.get('connections')
            if connections:
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        proc.kill()
                        return
        except:
            pass

def reset_all():
    """Сбросить все статусы"""
    hermes_start_btn.config(state=tk.NORMAL)
    hermes_stop_btn.config(state=tk.DISABLED)
    hermes_status.config(text="● Остановлен", foreground="red")
    
    gateway_start_btn.config(state=tk.NORMAL)
    gateway_stop_btn.config(state=tk.DISABLED)
    gateway_status.config(text="● Остановлен", foreground="red")
    
    dashboard_start_btn.config(state=tk.NORMAL)
    dashboard_stop_btn.config(state=tk.DISABLED)
    dashboard_status.config(text="● Остановлен", foreground="red")
    
    log_widget.insert(tk.END, "━" * 50 + "\n")
    log_widget.insert(tk.END, "🔄 Статусы сброшены\n")
    log_widget.insert(tk.END, "━" * 50 + "\n")
    log_widget.see(tk.END)

def show_help():
    """Показать справку"""
    help_text = """
═══════════════════════════════════════════════════════════════
                    КОМАНДЫ HERMES AGENT
═══════════════════════════════════════════════════════════════

/новый          - Начать новую сессию
/очистить       - Очистить экран
/повторить      - Повторить последнее сообщение
/отменить       - Отменить последний обмен
/сжать          - Сжать контекст разговора
/стоп           - Остановить фоновые процессы
/помощь         - Показать команды
/модель         - Сменить модель
/навыки         - Управление навыками
/инструменты    - Управление инструментами
/шлюз           - Настройки шлюза
/статус         - Информация о сессии
═══════════════════════════════════════════════════════════════
"""
    help_window = tk.Toplevel(root)
    help_window.title("📖 Справка")
    help_window.geometry("700x500")
    
    text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=80, height=30)
    text.pack(padx=10, pady=10)
    text.insert(tk.END, help_text)
    text.config(state=tk.DISABLED)
    
    ttk.Button(help_window, text="Закрыть", command=help_window.destroy).pack(pady=10)

# Создаём главное окно
root = tk.Tk()
root.title("🤖 Панель управления Hermes")
root.geometry("700x550")

# Заголовок
ttk.Label(root, text="🤖 Панель управления Hermes Agent", font=("Segoe UI", 16, "bold")).pack(pady=10)

# Фрейм управления
control_frame = ttk.LabelFrame(root, text="📋 Управление", padding=15)
control_frame.pack(fill=tk.X, padx=20, pady=10)

# Hermes
h_frame = ttk.Frame(control_frame)
h_frame.pack(fill=tk.X, pady=5)
ttk.Label(h_frame, text="Hermes:", width=15).pack(side=tk.LEFT)
hermes_start_btn = ttk.Button(h_frame, text="▶ Запустить", command=start_hermes, width=15)
hermes_start_btn.pack(side=tk.LEFT, padx=5)
hermes_stop_btn = ttk.Button(h_frame, text="⏹ Остановить", command=stop_hermes, width=15, state=tk.DISABLED)
hermes_stop_btn.pack(side=tk.LEFT, padx=5)
hermes_status = ttk.Label(h_frame, text="● Остановлен", foreground="red")
hermes_status.pack(side=tk.LEFT, padx=10)

# Gateway
g_frame = ttk.Frame(control_frame)
g_frame.pack(fill=tk.X, pady=5)
ttk.Label(g_frame, text="Gateway:", width=15).pack(side=tk.LEFT)
gateway_start_btn = ttk.Button(g_frame, text="▶ Запустить", command=start_gateway, width=15)
gateway_start_btn.pack(side=tk.LEFT, padx=5)
gateway_stop_btn = ttk.Button(g_frame, text="⏹ Остановить", command=stop_gateway, width=15, state=tk.DISABLED)
gateway_stop_btn.pack(side=tk.LEFT, padx=5)
gateway_status = ttk.Label(g_frame, text="● Остановлен", foreground="red")
gateway_status.pack(side=tk.LEFT, padx=10)

# Dashboard
d_frame = ttk.Frame(control_frame)
d_frame.pack(fill=tk.X, pady=5)
ttk.Label(d_frame, text="Dashboard:", width=15).pack(side=tk.LEFT)
dashboard_start_btn = ttk.Button(d_frame, text="▶ Запустить", command=start_dashboard, width=15)
dashboard_start_btn.pack(side=tk.LEFT, padx=5)
dashboard_stop_btn = ttk.Button(d_frame, text="⏹ Остановить", command=stop_dashboard, width=15, state=tk.DISABLED)
dashboard_stop_btn.pack(side=tk.LEFT, padx=5)
dashboard_status = ttk.Label(d_frame, text="● Остановлен", foreground="red")
dashboard_status.pack(side=tk.LEFT, padx=10)

# Кнопки действий
actions_frame = ttk.Frame(root)
actions_frame.pack(fill=tk.X, padx=20, pady=10)
ttk.Button(actions_frame, text="📖 Справка", command=show_help, width=20).pack(side=tk.LEFT, padx=5)
ttk.Button(actions_frame, text="🔄 Сбросить", command=reset_all, width=15).pack(side=tk.LEFT, padx=5)
ttk.Button(actions_frame, text="🚪 Выход", command=root.quit, width=15).pack(side=tk.RIGHT, padx=5)

# Лог
log_frame = ttk.LabelFrame(root, text="📝 Журнал", padding=10)
log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
log_widget.pack(fill=tk.BOTH, expand=True)

# Статус бар
status_bar = ttk.Label(root, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
status_bar.pack(fill=tk.X, padx=20, pady=5)

# Начальное сообщение
log_widget.insert(tk.END, "Панель управления запущена\n")
log_widget.insert(tk.END, f"Директория: {WORK_DIR}\n")
log_widget.insert(tk.END, "━" * 50 + "\n")

# Запуск
root.mainloop()
