#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hermes_control.py - Панель управления Hermes Agent

GUI-интерфейс для запуска/остановки:
- Hermes (основной интерфейс)
- Hermes Gateway
- Hermes Dashboard

Все надписи на русском языке.
Запуск через herLayStart.py (с русским языком).
"""

import os
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import psutil
import socket


# ============================================================================
# Константы
# ============================================================================

WORK_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = WORK_DIR / ".venv" / "Scripts" / "python.exe"

HERMES_LAUNCH_SCRIPT = "herLayStart.py"  # Запуск с русским языком!
HERMES_GATEWAY_CMD = "hermes_cli.main gateway"  # python -m hermes_cli.main gateway ...
HERMES_DASHBOARD_CMD = "hermes_cli.main dashboard"  # python -m hermes_cli.main dashboard

PORTS = {
    "dashboard": 9119,
    "gateway_webhook": 8644,
}

PROCESS_NAMES = {
    "hermes": "Hermes",
    "gateway": "Hermes Gateway",
    "dashboard": "Hermes Dashboard",
}


# ============================================================================
# Проверка процессов
# ============================================================================

def is_port_in_use(port: int) -> bool:
    """Проверить занят ли порт."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_hermes_process(cmd_pattern: str) -> bool:
    """Найти процесс Hermes по аргументам командной строки (быстро)."""
    try:
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and 'python' in ' '.join(cmdline).lower():
                    if cmd_pattern in ' '.join(cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return False


def check_process_status(process_name: str) -> bool:
    """
    Проверить запущен ли процесс.
    
    Args:
        process_name: 'hermes', 'gateway', или 'dashboard'
    
    Returns:
        True если запущен, False если нет
    """
    if process_name == "dashboard":
        # Dashboard проверяем по порту
        return is_port_in_use(PORTS["dashboard"])
    
    elif process_name == "gateway":
        # Gateway проверяем по процессу или порту
        if find_hermes_process(HERMES_GATEWAY_CMD):
            return True
        return is_port_in_use(PORTS["gateway_webhook"])
    
    elif process_name == "hermes":
        # Hermes проверяем по процессу herLayStart.py
        return find_hermes_process(HERMES_LAUNCH_SCRIPT)
    
    return False


# ============================================================================
# Запуск/Остановка процессов
# ============================================================================

def start_process(process_name: str, log_widget=None, app=None):
    """
    Запустить процесс в отдельном терминале.
    
    Args:
        process_name: 'hermes', 'gateway', или 'dashboard'
        log_widget: Виджет для вывода логов (опционально)
        app: Ссылка на приложение для переключения кнопок
    """
    # СРАЗУ переключаем кнопки в состояние "запущен"
    if app:
        app.set_process_running(process_name, True)
    
    # Для hermes не нужен cmd_map — запускаем напрямую через herLayStart.py
    if process_name == "hermes":
        title = PROCESS_NAMES.get(process_name, process_name)
        # Hermes - запускаем через herLayStart.py (с русским языком!)
        full_cmd = f'start "Hermes - {title}" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python {HERMES_LAUNCH_SCRIPT}"'
        
        try:
            subprocess.Popen(full_cmd, shell=True, cwd=str(WORK_DIR))
            if log_widget:
                log_widget.insert(tk.END, f"✓ {title} запущен\n")
                log_widget.see(tk.END)
        except Exception as e:
            if log_widget:
                log_widget.insert(tk.END, f"✗ Ошибка запуска {title}: {e}\n")
                log_widget.see(tk.END)
            # Возвращаем кнопки обратно если ошибка
            if app:
                app.set_process_running(process_name, False)
        return
    
    # Для gateway и dashboard — через hermes_cli.main
    cmd_map = {
        "gateway": ["hermes_cli.main", "gateway", "run"],   # run = foreground (Windows)
        "dashboard": ["hermes_cli.main", "dashboard"],
    }
    
    if process_name not in cmd_map:
        if log_widget:
            log_widget.insert(tk.END, f"✗ Неизвестный процесс: {process_name}\n")
            log_widget.see(tk.END)
        if app:
            app.set_process_running(process_name, False)
        return
    
    cmd = cmd_map[process_name]
    title = PROCESS_NAMES.get(process_name, process_name)
    
    # Команда для запуска в новом окне cmd
    full_cmd = f'start "Hermes - {title}" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python -m {" ".join(cmd)}"'
    
    try:
        subprocess.Popen(full_cmd, shell=True, cwd=str(WORK_DIR))
        if log_widget:
            log_widget.insert(tk.END, f"✓ {title} запущен\n")
            log_widget.see(tk.END)
    except Exception as e:
        if log_widget:
            log_widget.insert(tk.END, f"✗ Ошибка запуска {title}: {e}\n")
            log_widget.see(tk.END)
        # Возвращаем кнопки обратно если ошибка
        if app:
            app.set_process_running(process_name, False)


def stop_process(process_name: str, log_widget=None, app=None):
    """
    Остановить процесс.
    
    Args:
        process_name: 'hermes', 'gateway', или 'dashboard'
        log_widget: Виджет для вывода логов (опционально)
        app: Ссылка на приложение для переключения кнопок
    """
    title = PROCESS_NAMES.get(process_name, process_name)
    
    # СРАЗУ переключаем кнопки в состояние "остановлен"
    if app:
        app.set_process_running(process_name, False)
    
    try:
        if process_name == "dashboard":
            # Dashboard останавливаем через порт (находим процесс и убиваем)
            stopped = kill_process_by_port(PORTS["dashboard"])
        elif process_name == "gateway":
            # Gateway останавливаем по процессу
            stopped = kill_hermes_process(HERMES_GATEWAY_CMD)
        elif process_name == "hermes":
            # Hermes останавливаем по процессу herLayStart.py
            stopped = kill_hermes_process(HERMES_LAUNCH_SCRIPT)
        else:
            stopped = False
        
        if log_widget:
            if stopped:
                log_widget.insert(tk.END, f"✓ {title} остановлен\n")
                log_widget.see(tk.END)
            else:
                log_widget.insert(tk.END, f"⚠ {title} не найден или уже остановлен\n")
                log_widget.see(tk.END)
                
    except Exception as e:
        if log_widget:
            log_widget.insert(tk.END, f"✗ Ошибка остановки {title}: {e}\n")
            log_widget.see(tk.END)


def kill_process_by_port(port: int) -> bool:
    """Убить процесс использующий указанный порт."""
    killed = False
    try:
        for proc in psutil.process_iter(['pid', 'connections']):
            try:
                connections = proc.info.get('connections')
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            proc.kill()
                            killed = True
                            return True  # Выходим сразу после убийства
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return killed


def kill_hermes_process(cmd_pattern: str) -> bool:
    """Убить процесс Hermes по аргументам командной строки."""
    killed = False
    try:
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline:
                    cmdline_str = ' '.join(cmdline)
                    if 'python' in cmdline_str.lower() and cmd_pattern in cmdline_str:
                        proc.kill()
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return killed


# ============================================================================
# Справка по командам
# ============================================================================

def show_help():
    """Показать справку по командам Hermes."""
    help_window = tk.Toplevel()
    help_window.title("📖 Справка по командам Hermes")
    help_window.geometry("900x700")
    
    # Делаем окно модальным
    help_window.transient(root)
    help_window.grab_set()
    
    # Заголовок
    title_label = ttk.Label(
        help_window, 
        text="Справка по командам Hermes Agent",
        font=("Segoe UI", 16, "bold")
    )
    title_label.pack(pady=10)
    
    # Текстовое поле с прокруткой
    text_widget = scrolledtext.ScrolledText(
        help_window, 
        wrap=tk.WORD, 
        width=100, 
        height=35,
        font=("Consolas", 10)
    )
    text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    # Текст справки
    help_text = """
═══════════════════════════════════════════════════════════════════════════════
                    СПРАВКА ПО КОМАНДАМ HERMES AGENT
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                           СЕССИЯ                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ /new [name]         - Начать новую сессию (свежий ID + история)              │
│ /reset              - Начать новую сессию (свежий ID + история)              │
│ /clear              - Очистить экран и начать новую сессию                   │
│ /redraw             - Принудительно перерисовать UI (восстанавливает         │
│                       после сбоев терминала)                                  │
│ /history            - Показать историю разговора                             │
│ /save               - Сохранить текущий разговор                             │
│ /retry              - Повторить последнее сообщение (отправить агенту        │
│                       повторно)                                               │
│ /undo               - Удалить последний обмен пользователь/ассистент         │
│ /title [name]       - Установить заголовок для текущей сессии                │
│ /branch [name]      - Ответвить текущую сессию (исследовать другой путь)     │
│ /fork [name]        - Ответвить текущую сессию (исследовать другой путь)     │
│ /compress [topic]   - Вручную сжать контекст разговора                       │
│ /rollback [number]  - Список или восстановление чекпоинтов файловой системы  │
│ /snapshot [create|restore <id>|prune] - Создать или восстановить снимки     │
│                       состояния конфигурации/состояния Hermes                 │
│ /snap               - Создать или восстановить снимки состояния              │
│ /stop               - Убить все запущенные фоновые процессы                  │
│ /background <prompt> - Запустить запрос в фоновом режиме                     │
│ /bg <prompt>        - Запустить запрос в фоновом режиме                      │
│ /agents             - Показать активные агенты и запущенные задачи           │
│ /tasks              - Показать активные агенты и запущенные задачи           │
│ /queue <prompt>     - Поставить запрос в очередь для следующего хода         │
│                       (не прерывает)                                          │
│ /q <prompt>         - Поставить запрос в очередь для следующего хода         │
│ /steer <prompt>     - Вставить сообщение после следующего вызова инструмента │
│                       без прерывания                                          │
│ /goal [text|pause|resume|clear|status] - Установить постоянную цель, над    │
│                       которой Hermes работает до достижения                   │
│ /subgoal [text|remove N|clear] - Добавить или управлять дополнительными     │
│                       критериями для активной цели                            │
│ /status             - Показать информацию о сессии                           │
│ /resume [name]      - Возобновить ранее названную сессию                     │
│ /sessions           - Просмотр и возобновление предыдущих сессий             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         КОНФИГУРАЦИЯ                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ /config             - Показать текущую конфигурацию                          │
│ /model [model] [--provider name] [--global] - Переключить модель для этой  │
│                       сессии                                                  │
│ /provider [model]   - Переключить модель для этой сессии                     │
│ /personality [name] - Установить предопределённую личность                   │
│ /statusbar          - Переключить строку состояния контекста/модели          │
│ /sb                 - Переключить строку состояния контекста/модели          │
│ /verbose            - Переключить отображение прогресса инструментов:        │
│                       off -> new -> all -> verbose                            │
│ /footer [on|off|status] - Переключить футер метаданных шлюза на финальных  │
│                       ответах                                                 │
│ /yolo               - Переключить режим YOLO (пропуск всех одобрений         │
│                       опасных команд)                                         │
│ /reasoning [level|show|hide] - Управление усилием рассуждения и             │
│                       отображением                                            │
│ /fast [normal|fast|status] - Переключить быстрый режим — OpenAI Priority   │
│                       Processing / Anthropic Fast Mode                        │
│ /skin [name]        - Показать или сменить скин/тему отображения             │
│ /voice [on|off|tts|status] - Переключить голосовой режим                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      ИНСТРУМЕНТЫ И НАВЫКИ                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ /tools [list|disable|enable] [name...] - Управление инструментами           │
│ /toolsets           - Список доступных наборов инструментов                  │
│ /skills [search|browse|inspect|install] - Поиск, установка, проверка или   │
│                       управление навыками                                    │
│ /cron [list|add|create|edit|pause|resume|run|remove] - Управление          │
│                       запланированными задачами                             │
│ /curator [status|run|pause|resume|pin|unpin|restore|list-archived] -       │
│                       Фоновое обслуживание навыков                           │
│ /kanban [list|ls|show|create|assign|link|unlink|claim|comment|complete|    │
│          block|unblock|archive|tail|dispatch|context|init|gc] - Доска       │
│                       многопрофильного сотрудничества                       │
│ /reload             - Перезагрузить переменные .env в текущую сессию         │
│ /reload-mcp         - Перезагрузить MCP серверы из конфигурации              │
│ /reload-skills      - Повторное сканирование ~/.hermes/skills/ на новые или │
│                       удалённые навыки                                        │
│ /browser [connect|disconnect|status] - Подключить инструменты браузера к   │
│                       живому Chrome через CDP                                 │
│ /plugins            - Список установленных плагинов и их статус              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ИНФОРМАЦИЯ                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ /help               - Показать доступные команды                             │
│ /commands [page]    - Просмотр всех команд и навыков (постранично)           │
│ /usage              - Показать использование токенов и лимиты для текущей   │
│                       сессии                                                  │
│ /insights [days]    - Показать аналитику и инсайты использования             │
│ /platforms          - Показать статус платформы шлюза/сообщений              │
│ /whoami             - Показать доступ к командам (админ / пользователь)      │
│ /profile            - Показать активный профиль и домашний каталог           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ВЫХОД                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ /quit               - Выйти из Hermes                                        │
│ /exit               - Выйти из Hermes                                        │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                            СОВЕТЫ ПО ИСПОЛЬЗОВАНИЮ
═══════════════════════════════════════════════════════════════════════════════

• Используйте Tab для автодополнения команд
• Стрелки ВВЕРХ/ВНИЗ для навигации по истории команд
• Ctrl+C для прерывания текущей операции
• /help <command> для получения справки по конкретной команде

═══════════════════════════════════════════════════════════════════════════════
"""
    
    text_widget.insert(tk.END, help_text)
    text_widget.config(state=tk.DISABLED)  # Только для чтения
    
    # Кнопка закрытия
    close_button = ttk.Button(help_window, text="Закрыть", command=help_window.destroy)
    close_button.pack(pady=10)


# ============================================================================
# GUI Приложение
# ============================================================================

class HermesControlApp:
    """Основное приложение панели управления."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Панель управления Hermes Agent")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Статусы процессов
        self.statuses = {
            "hermes": False,
            "gateway": False,
            "dashboard": False,
        }
        self._stop_monitor = threading.Event()
        
        # Создаём интерфейс
        self.create_widgets()
        
        # Проверяем реальные статусы при запуске
        self.refresh_all_statuses()
        
        # Запускаем фоновый монитор статуса (каждые 3 секунды)
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()
    
    def create_widgets(self):
        """Создать виджеты интерфейса."""
        
        # Заголовок
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title_label = ttk.Label(
            title_frame,
            text="🤖 Панель управления Hermes Agent",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Управление процессами Hermes",
            font=("Segoe UI", 10)
        )
        subtitle_label.pack()
        
        # Разделитель
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Фрейм для кнопок управления
        control_frame = ttk.LabelFrame(self.root, text="📋 Управление процессами", padding=15)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Hermes CLI
        hermes_frame = ttk.Frame(control_frame)
        hermes_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hermes_frame, text="Hermes (Терминал):", width=25, anchor='w').pack(side=tk.LEFT)
        
        self.hermes_start_btn = ttk.Button(
            hermes_frame,
            text="▶ Запустить",
            command=lambda: start_process("hermes", self.log_widget, self),
            width=15
        )
        self.hermes_start_btn.pack(side=tk.LEFT, padx=5)

        self.hermes_stop_btn = ttk.Button(
            hermes_frame,
            text="⏹ Остановить",
            command=lambda: stop_process("hermes", self.log_widget, self),
            width=15,
            state=tk.DISABLED
        )
        self.hermes_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.hermes_status_label = ttk.Label(hermes_frame, text="● Остановлен", foreground="red")
        self.hermes_status_label.pack(side=tk.LEFT, padx=10)
        
        # Gateway
        gateway_frame = ttk.Frame(control_frame)
        gateway_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(gateway_frame, text="Hermes Gateway:", width=25, anchor='w').pack(side=tk.LEFT)
        
        self.gateway_start_btn = ttk.Button(
            gateway_frame,
            text="▶ Запустить",
            command=lambda: start_process("gateway", self.log_widget, self),
            width=15
        )
        self.gateway_start_btn.pack(side=tk.LEFT, padx=5)

        self.gateway_stop_btn = ttk.Button(
            gateway_frame,
            text="⏹ Остановить",
            command=lambda: stop_process("gateway", self.log_widget, self),
            width=15,
            state=tk.DISABLED
        )
        self.gateway_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.gateway_status_label = ttk.Label(gateway_frame, text="● Остановлен", foreground="red")
        self.gateway_status_label.pack(side=tk.LEFT, padx=10)
        
        # Dashboard
        dashboard_frame = ttk.Frame(control_frame)
        dashboard_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dashboard_frame, text="Hermes Dashboard:", width=25, anchor='w').pack(side=tk.LEFT)
        
        self.dashboard_start_btn = ttk.Button(
            dashboard_frame,
            text="▶ Запустить",
            command=lambda: start_process("dashboard", self.log_widget, self),
            width=15
        )
        self.dashboard_start_btn.pack(side=tk.LEFT, padx=5)

        self.dashboard_stop_btn = ttk.Button(
            dashboard_frame,
            text="⏹ Остановить",
            command=lambda: stop_process("dashboard", self.log_widget, self),
            width=15,
            state=tk.DISABLED
        )
        self.dashboard_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.dashboard_status_label = ttk.Label(dashboard_frame, text="● Остановлен", foreground="red")
        self.dashboard_status_label.pack(side=tk.LEFT, padx=10)
        
        # Разделитель
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Фрейм для кнопок действий
        actions_frame = ttk.Frame(self.root)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.help_btn = ttk.Button(
            actions_frame,
            text="📖 Справка по командам",
            command=show_help,
            width=25
        )
        self.help_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(
            actions_frame,
            text="🔄 Обновить статусы",
            command=self.refresh_all_statuses,
            width=20
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка выхода
        self.exit_btn = ttk.Button(
            actions_frame,
            text="🚪 Выход",
            command=self.root.quit,
            width=15
        )
        self.exit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Разделитель
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Лог
        log_frame = ttk.LabelFrame(self.root, text="📝 Журнал событий", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_widget = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=10,
            font=("Consolas", 9)
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True)
        
        # Начальное сообщение в логе
        self.log_widget.insert(tk.END, "Панель управления Hermes Agent запущена\n")
        self.log_widget.insert(tk.END, f"Рабочая директория: {WORK_DIR}\n")
        self.log_widget.insert(tk.END, "─" * 60 + "\n")
        self.log_widget.see(tk.END)
        
        # Статус бар
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.status_bar_label = ttk.Label(
            status_frame,
            text="Готово",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar_label.pack(fill=tk.X)

    def update_process_ui(self, process_name: str, is_running: bool):
        """
        Обновить UI для процесса.
        
        Args:
            process_name: 'hermes', 'gateway', или 'dashboard'
            is_running: True если запущен
        """
        if process_name == "hermes":
            start_btn = self.hermes_start_btn
            stop_btn = self.hermes_stop_btn
            status_label = self.hermes_status_label
        elif process_name == "gateway":
            start_btn = self.gateway_start_btn
            stop_btn = self.gateway_stop_btn
            status_label = self.gateway_status_label
        elif process_name == "dashboard":
            start_btn = self.dashboard_start_btn
            stop_btn = self.dashboard_stop_btn
            status_label = self.dashboard_status_label
        else:
            return
        
        # Переключаем кнопки
        if is_running:
            # Запущен
            start_btn.config(state=tk.DISABLED)
            stop_btn.config(state=tk.NORMAL)
            status_label.config(text="● Запущен", foreground="green")
        else:
            # Остановлен
            start_btn.config(state=tk.NORMAL)
            stop_btn.config(state=tk.DISABLED)
            status_label.config(text="● Остановлен", foreground="red")
        
        # Принудительно обновляем кнопки
        start_btn.update()
        stop_btn.update()
        status_label.update()
    
    def refresh_all_statuses(self):
        """Проверить реальные статусы всех процессов и обновить UI."""
        for process_name in self.statuses.keys():
            is_running = check_process_status(process_name)
            self.set_process_running(process_name, is_running)
        self.status_bar_label.config(
            text="Статусы обновлены: " + time.strftime("%H:%M:%S")
        )

    def _monitor_loop(self):
        """Фоновый цикл проверки статусов."""
        while not self._stop_monitor.is_set():
            self._stop_monitor.wait(3)  # Проверяем каждые 3 секунды
            if self._stop_monitor.is_set():
                break
            for process_name in self.statuses.keys():
                is_running = check_process_status(process_name)
                # Обновляем UI только если статус изменился
                if self.statuses.get(process_name) != is_running:
                    self.root.after(0, self.set_process_running, process_name, is_running)
            # Обновляем строку состояния
            self.root.after(0, lambda: self.status_bar_label.config(
                text="Мониторинг активен: " + time.strftime("%H:%M:%S")
            ))
    
    def on_close(self):
        """Обработчик закрытия окна — останавливаем монитор."""
        self._stop_monitor.set()
        self.root.quit()
        self.root.destroy()
    
    def set_process_running(self, process_name: str, is_running: bool):
        """
        Переключить кнопки процесса (БЕЗ ПРОВЕРКИ!).
        
        Args:
            process_name: 'hermes', 'gateway', или 'dashboard'
            is_running: True если запущен
        """
        self.statuses[process_name] = is_running
        self.update_process_ui(process_name, is_running)
    
    def reset_all_statuses(self):
        """Сбросить все статусы в 'остановлен'."""
        for process_name in self.statuses.keys():
            self.statuses[process_name] = False
            self.update_process_ui(process_name, False)
        
        # Запись в журнал (если журнал уже создан)
        if hasattr(self, 'log_widget') and self.log_widget:
            self.log_widget.insert(tk.END, "━" * 50 + "\n")
            self.log_widget.insert(tk.END, "🔄 Статусы сброшены (автоматически при запуске)\n")
            self.log_widget.insert(tk.END, "━" * 50 + "\n")
            self.log_widget.see(tk.END)
        
        self.status_bar_label.config(text="Статусы сброшены: " + time.strftime("%H:%M:%S"))
        # Принудительно обновляем ВСЁ окно
        self.root.update_idletasks()
        self.root.update()


# ============================================================================
# Главная функция
# ============================================================================

def main():
    """Главная функция."""
    global root
    
    # Проверяем зависимости
    try:
        import psutil
    except ImportError:
        messagebox.showerror(
            "Ошибка",
            "Не установлен модуль psutil!\n\n"
            "Установите командой:\n"
            ".venv\\Scripts\\activate\n"
            "pip install psutil"
        )
        sys.exit(1)
    
    # Проверяем рабочую директорию
    if not VENV_PYTHON.exists():
        messagebox.showerror(
            "Ошибка",
            f"Виртуальное окружение не найдено!\n\n"
            f"Путь: {VENV_PYTHON}\n\n"
            "Создайте его командами:\n"
            "uv venv .venv --python 3.12\n"
            ".venv\\Scripts\\activate\n"
            "uv pip install -e \".[all]\""
        )
        sys.exit(1)
    
    # Создаём главное окно
    root = tk.Tk()
    
    # Устанавливаем стиль
    style = ttk.Style()
    style.theme_use('vista')  # Современный стиль Windows
    
    # Создаём приложение
    app = HermesControlApp(root)
    
    # Обработчик закрытия окна
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Запускаем главный цикл
    root.mainloop()


if __name__ == "__main__":
    main()
