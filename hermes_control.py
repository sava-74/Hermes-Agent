#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hermes_control.py - Полноценная панель управления Hermes Agent

Вкладки:
1. 🚀 Процессы: Запуск/остановка Hermes, Gateway, Dashboard, API Server.
2. ⚙️ Настройки: Редактирование config.yaml (Модель, Провайдер, Ключи, Тулсеты).
3. 📊 Статистика: Просмотр расхода токенов и истории запросов.
"""

import os
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pathlib import Path
import psutil
import socket
import json

try:
    import yaml
except ImportError:
    messagebox.showerror("Ошибка", "Не установлен модуль pyyaml!\n\nУстановите: pip install pyyaml")
    sys.exit(1)


# ============================================================================
# Константы
# ============================================================================

WORK_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = WORK_DIR / ".venv" / "Scripts" / "python.exe"
HERMES_HOME = Path.home() / ".hermes"
CONFIG_FILE = HERMES_HOME / "config.yaml"
STATS_FILE = HERMES_HOME / "hermes_api_stats.json"

HERMES_LAUNCH_SCRIPT = "herLayStart.py"
HERMES_GATEWAY_CMD = "hermes_cli.main gateway"
HERMES_DASHBOARD_CMD = "hermes_cli.main dashboard"
HERMES_API_SERVER_CMD = "api_server.py"

PORTS = {
    "dashboard": 9119,
    "gateway_webhook": 8644,
    "api_server": 8765,
}

PROCESS_NAMES = {
    "hermes": "Hermes (Терминал)",
    "gateway": "Hermes Gateway",
    "dashboard": "Hermes Dashboard",
    "api_server": "Hermes API Server",
}


# ============================================================================
# Проверка процессов
# ============================================================================

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_hermes_process(cmd_pattern: str) -> bool:
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
    if process_name == "dashboard":
        return is_port_in_use(PORTS["dashboard"])
    elif process_name == "gateway":
        if find_hermes_process(HERMES_GATEWAY_CMD):
            return True
        return is_port_in_use(PORTS["gateway_webhook"])
    elif process_name == "hermes":
        return find_hermes_process(HERMES_LAUNCH_SCRIPT)
    elif process_name == "api_server":
        return is_port_in_use(PORTS["api_server"])
    return False


# ============================================================================
# Запуск/Остановка процессов
# ============================================================================

def start_process(process_name: str, log_widget=None, app=None):
    if app:
        app.set_process_running(process_name, True)
    
    if process_name == "hermes":
        title = PROCESS_NAMES.get(process_name, process_name)
        full_cmd = f'start "Hermes - {title}" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python {HERMES_LAUNCH_SCRIPT}"'
    elif process_name == "api_server":
        title = PROCESS_NAMES.get(process_name, process_name)
        full_cmd = f'start "Hermes - {title}" cmd.exe /k "cd /d "{WORK_DIR}" && .venv\\Scripts\\activate && python {HERMES_API_SERVER_CMD}"'
    else:
        cmd_map = {
            "gateway": ["hermes_cli.main", "gateway", "run"],
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
        if app:
            app.set_process_running(process_name, False)


def stop_process(process_name: str, log_widget=None, app=None):
    title = PROCESS_NAMES.get(process_name, process_name)
    if app:
        app.set_process_running(process_name, False)
    
    try:
        if process_name == "dashboard":
            stopped = kill_process_by_port(PORTS["dashboard"])
        elif process_name == "gateway":
            stopped = kill_hermes_process(HERMES_GATEWAY_CMD)
        elif process_name == "hermes":
            stopped = kill_hermes_process(HERMES_LAUNCH_SCRIPT)
        elif process_name == "api_server":
            stopped = kill_hermes_process(HERMES_API_SERVER_CMD)
            if not stopped:
                stopped = kill_process_by_port(PORTS["api_server"])
        else:
            stopped = False
        
        if log_widget:
            if stopped:
                log_widget.insert(tk.END, f"✓ {title} остановлен\n")
            else:
                log_widget.insert(tk.END, f"⚠ {title} не найден\n")
            log_widget.see(tk.END)
    except Exception as e:
        if log_widget:
            log_widget.insert(tk.END, f"✗ Ошибка остановки {title}: {e}\n")
            log_widget.see(tk.END)

def kill_process_by_port(port: int) -> bool:
    killed = False
    try:
        for proc in psutil.process_iter(['pid', 'connections']):
            try:
                connections = proc.info.get('connections')
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            parent = psutil.Process(proc.info['pid'])
                            children = parent.children(recursive=True)
                            for child in children:
                                try: child.kill()
                                except: pass
                            
                            gone, alive = psutil.wait_procs(children, timeout=2)
                            for s in alive:
                                try: s.kill()
                                except: pass
                            
                            try:
                                parent.kill()
                                parent.wait(timeout=3)
                                killed = True
                            except: pass
                            return True
            except: continue
    except: pass
    return killed

def kill_hermes_process(cmd_pattern: str) -> bool:
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
            except: continue
    except: pass
    return killed


# ============================================================================
# Управление конфигурацией
# ============================================================================

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_config(data: dict):
    existing = load_config()
    # Простое слияние (можно улучшить)
    existing.update(data)
    
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True)
    return True

def get_env_var(name: str) -> str:
    # Читаем из .env файла Hermes если есть
    env_file = HERMES_HOME / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip()
    return os.getenv(name, "")


# ============================================================================
# GUI Приложение
# ============================================================================

class HermesControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Панель управления Hermes Agent")
        self.root.geometry("900x650")
        
        self.statuses = {"hermes": False, "gateway": False, "dashboard": False, "api_server": False}
        self._stop_monitor = threading.Event()
        
        self.create_widgets()
        self.refresh_all_statuses()
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def create_widgets(self):
        # Заголовок
        ttk.Label(self.root, text="🤖 Панель управления Hermes Agent", font=("Segoe UI", 18, "bold")).pack(pady=10)
        
        # Вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.create_processes_tab()
        self.create_settings_tab()
        self.create_stats_tab()
        
        # Строка статуса
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        self.status_bar_label = ttk.Label(status_frame, text="Готово", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar_label.pack(fill=tk.X)
        
        # Лог
        log_frame = ttk.LabelFrame(self.root, text="📝 Журнал событий", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_widget = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_widget.pack(fill=tk.BOTH, expand=True)
        self.log_widget.insert(tk.END, "Панель управления запущена\n")

    def create_processes_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🚀 Процессы")
        
        control_frame = ttk.LabelFrame(tab, text="Управление процессами", padding=15)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self._add_process_row(control_frame, "hermes")
        self._add_process_row(control_frame, "gateway")
        self._add_process_row(control_frame, "dashboard")
        self._add_process_row(control_frame, "api_server")
        
        ttk.Button(tab, text="🔄 Обновить все статусы", command=self.refresh_all_statuses).pack(pady=10)

    def _add_process_row(self, parent, name):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame, text=PROCESS_NAMES[name], width=25, anchor='w').pack(side=tk.LEFT)
        
        btn_start = ttk.Button(frame, text="▶ Запустить", command=lambda: start_process(name, self.log_widget, self), width=15)
        btn_start.pack(side=tk.LEFT, padx=5)
        setattr(self, f"{name}_start_btn", btn_start)
        
        btn_stop = ttk.Button(frame, text="⏹ Остановить", command=lambda: stop_process(name, self.log_widget, self), width=15, state=tk.DISABLED)
        btn_stop.pack(side=tk.LEFT, padx=5)
        setattr(self, f"{name}_stop_btn", btn_stop)
        
        status_lbl = ttk.Label(frame, text="● Остановлен", foreground="red")
        status_lbl.pack(side=tk.LEFT, padx=10)
        setattr(self, f"{name}_status_label", status_lbl)

    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ Настройки")
        
        # Чтение конфига
        config = load_config()
        model_cfg = config.get("model", {})
        
        settings_frame = ttk.LabelFrame(tab, text="Конфигурация (~/.hermes/config.yaml)", padding=15)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Провайдер
        ttk.Label(settings_frame, text="Провайдер (model.provider):").pack(anchor=tk.W, padx=5, pady=2)
        self.var_provider = tk.StringVar(value=model_cfg.get("provider", "alibaba"))
        ttk.Entry(settings_frame, textvariable=self.var_provider).pack(fill=tk.X, padx=5, pady=2)
        
        # Модель
        ttk.Label(settings_frame, text="Модель (model.default):").pack(anchor=tk.W, padx=5, pady=2)
        self.var_model = tk.StringVar(value=model_cfg.get("default", "qwen-plus"))
        ttk.Entry(settings_frame, textvariable=self.var_model).pack(fill=tk.X, padx=5, pady=2)
        
        # API Ключ (только чтение/маскировка для безопасности, редактирование через файл)
        ttk.Label(settings_frame, text="API Key (см. ~/.hermes/.env):").pack(anchor=tk.W, padx=5, pady=2)
        dash_key = get_env_var("DASHSCOPE_API_KEY")
        masked_key = (dash_key[:4] + "..." + dash_key[-4:]) if len(dash_key) > 8 else "Не найден"
        ttk.Label(settings_frame, text=masked_key, font=("Consolas", 10)).pack(fill=tk.X, padx=5, pady=2)
        
        # Кнопки
        btn_frame = ttk.Frame(settings_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="💾 Сохранить изменения", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Открыть config.yaml", command=lambda: os.startfile(CONFIG_FILE)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Открыть .env", command=lambda: os.startfile(HERMES_HOME / ".env")).pack(side=tk.LEFT, padx=5)
        
        self.settings_log = ttk.Label(settings_frame, text="", foreground="green")
        self.settings_log.pack(anchor=tk.W, padx=5, pady=5)

    def _save_settings(self):
        try:
            data = {
                "model": {
                    "provider": self.var_provider.get(),
                    "default": self.var_model.get()
                }
            }
            save_config(data)
            self.settings_log.config(text="✅ Настройки сохранены! Перезапустите процессы.")
            self.log_widget.insert(tk.END, "✅ Настройки сохранены в config.yaml\n")
        except Exception as e:
            self.settings_log.config(text=f"❌ Ошибка: {e}")

    def create_stats_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Статистика")
        
        stats_frame = ttk.LabelFrame(tab, text="Расход токенов (локальный учет)", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Основные метрики
        metrics_frame = ttk.Frame(stats_frame)
        metrics_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_total_tokens = ttk.Label(metrics_frame, text="Всего токенов: 0", font=("Segoe UI", 14, "bold"))
        self.lbl_total_tokens.pack(side=tk.LEFT, padx=20)
        
        self.lbl_last_req = ttk.Label(metrics_frame, text="Последний запрос: -", font=("Segoe UI", 10))
        self.lbl_last_req.pack(side=tk.LEFT, padx=20)
        
        # Таблица истории
        tree_frame = ttk.Frame(stats_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Time", "Prompt", "Completion", "Total", "Model"), show='headings')
        self.tree.heading("Time", text="Время")
        self.tree.heading("Prompt", text="Входные (Prompt)")
        self.tree.heading("Completion", text="Исходящие (Completion)")
        self.tree.heading("Total", text="Всего")
        self.tree.heading("Model", text="Модель")
        
        self.tree.column("Time", width=120)
        self.tree.column("Prompt", width=80, anchor=tk.CENTER)
        self.tree.column("Completion", width=80, anchor=tk.CENTER)
        self.tree.column("Total", width=80, anchor=tk.CENTER)
        self.tree.column("Model", width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Кнопка обновления
        ttk.Button(stats_frame, text="🔄 Обновить статистику", command=self.update_stats_display).pack(pady=5)

    def update_stats_display(self):
        # Очистка
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                
                total = stats.get("total_tokens", 0)
                last_req = stats.get("last_request", "-")
                
                self.lbl_total_tokens.config(text=f"Всего токенов: {total}")
                self.lbl_last_req.config(text=f"Последний запрос: {last_req}")
                
                history = stats.get("history", [])
                for row in reversed(history):
                    self.tree.insert("", tk.END, values=(
                        row.get("time", ""),
                        row.get("prompt", 0),
                        row.get("completion", 0),
                        row.get("total", 0),
                        row.get("model", "Hermes")
                    ))
            except Exception:
                pass

    # ... (Methods for process status updates same as before) ...
    
    def set_process_running(self, process_name: str, is_running: bool):
        self.statuses[process_name] = is_running
        self.update_process_ui(process_name, is_running)

    def update_process_ui(self, process_name: str, is_running: bool):
        start_btn = getattr(self, f"{process_name}_start_btn", None)
        stop_btn = getattr(self, f"{process_name}_stop_btn", None)
        status_label = getattr(self, f"{process_name}_status_label", None)
        
        if start_btn and stop_btn and status_label:
            if is_running:
                start_btn.config(state=tk.DISABLED)
                stop_btn.config(state=tk.NORMAL)
                status_label.config(text="● Запущен", foreground="green")
            else:
                start_btn.config(state=tk.NORMAL)
                stop_btn.config(state=tk.DISABLED)
                status_label.config(text="● Остановлен", foreground="red")
            start_btn.update(); stop_btn.update(); status_label.update()

    def refresh_all_statuses(self):
        for name in self.statuses:
            is_running = check_process_status(name)
            self.set_process_running(name, is_running)
        self.status_bar_label.config(text="Статусы обновлены: " + time.strftime("%H:%M:%S"))
        self.update_stats_display()

    def _monitor_loop(self):
        while not self._stop_monitor.is_set():
            self._stop_monitor.wait(3)
            if self._stop_monitor.is_set(): break
            for name in self.statuses:
                is_running = check_process_status(name)
                if self.statuses.get(name) != is_running:
                    self.root.after(0, self.set_process_running, name, is_running)

    def on_close(self):
        self._stop_monitor.set()
        self.root.quit()
        self.root.destroy()


def main():
    global root
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('vista')
    
    app = HermesControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
