"""Движок скинов/тем для Hermes CLI.

Данная система скинов позволяет пользователям настраивать визуальный вид CLI.
Скины определяются как YAML-файлы в ~/.hermes/skins/ или как встроенные пресеты.
Для добавления нового скина не требуется изменений кода.

СХЕМА YAML ДЛЯ СКИНОВ
=====================

Все поля необязательны. Недостающие значения наследуются от скина ``default``.

.. code-block:: yaml

    # Обязательно: идентификатор скина
    name: mytheme                         # Уникальное имя скина (нижний регистр, дефисы допустимы)
    description: Краткое описание         # Показывается в списке /skin

    # Цвета: hex-значения для разметки Rich (баннер, UI, окно ответа)
    colors:
      banner_border: "#CD7F32"            # Цвет границы панели
      banner_title: "#FFD700"             # Цвет текста заголовка панели
      banner_accent: "#FFBF00"            # Заголовки разделов (Доступные инструменты и т.д.)
      banner_dim: "#B8860B"               # Приглушённый/неяркий текст (разделители, метки)
      banner_text: "#FFF8DC"              # Основной текст (имена инструментов, имена скиллов)
      ui_accent: "#FFBF00"               # Общий акцент UI
      ui_label: "#DAA520"                # Метки UI (тёплое золото; бирюзовый конфликтовал с золотым баннером)
      ui_ok: "#4caf50"                   # Индикаторы успеха
      ui_error: "#ef5350"                # Индикаторы ошибок
      ui_warn: "#ffa726"                 # Индикаторы предупреждений
      prompt: "#FFF8DC"                  # Цвет текста приглашения
      input_rule: "#CD7F32"              # Горизонтальная линия области ввода
      response_border: "#FFD700"         # Граница окна ответа (ANSI)
      status_bar_bg: "#1a1a2e"           # Фон статус-бара
      status_bar_text: "#C0C0C0"         # Текст статус-бара по умолчанию
      status_bar_strong: "#FFD700"       # Выделенный текст статус-бара
      status_bar_dim: "#8B8682"          # Разделители/приглушённый текст статус-бара
      status_bar_good: "#8FBC8F"         # Здоровое использование контекста
      status_bar_warn: "#FFD700"         # Предупреждающее использование контекста
      status_bar_bad: "#FF8C00"          # Высокое использование контекста
      status_bar_critical: "#FF6B6B"     # Критическое использование контекста
      session_label: "#DAA520"           # Цвет метки сессии
      session_border: "#8B8682"          # Цвет ID сессии
      status_bar_bg: "#1a1a2e"          # Фон статус-бара/панели использования TUI
      voice_status_bg: "#1a1a2e"        # Фон статуса голоса TUI
      selection_bg: "#333355"           # Фон выделения мыши TUI
      completion_menu_bg: "#1a1a2e"      # Фон меню автодополнения
      completion_menu_current_bg: "#333355"  # Фон активной строки меню автодополнения
      completion_menu_meta_bg: "#1a1a2e"     # Фон столбца метаданных меню автодополнения
      completion_menu_meta_current_bg: "#333355"  # Фон активных метаданных меню автодополнения

    # Спиннер: настройка анимированного спиннера во время API-вызовов
    spinner:
      waiting_faces:                      # Лица, показываемые во время ожидания API
        - "(⚔)"
        - "(⛨)"
      thinking_faces:                     # Лица, показываемые во время размышлений
        - "(⌁)"
        - "(<>)"
      thinking_verbs:                     # Глаголы для сообщений спиннера
        - "forging"
        - "plotting"
      wings:                              # Необязательные левые/правые украшения спиннера
        - ["⟪⚔", "⚔⟫"]                  # Каждая запись — пара [левый, правый]
        - ["⟪▲", "▲⟫"]

    # Брендинг: текстовые строки, используемые throughout CLI
    branding:
      agent_name: "Hermes Agent"          # Заголовок баннера, отображение статуса
      welcome: "Приветственное сообщение" # Показывается при запуске CLI
      goodbye: "До свидания! ⚕"          # Показывается при выходе
      response_label: " ⚕ Hermes "       # Заголовок окна ответа
      prompt_symbol: "❯"                 # Символ приглашения ввода (голый токен; рендереры добавляют пробел)
      help_header: "(^_^)? Команды"       # Текст заголовка /help

    # Префикс инструмента: символ для строк вывода инструмента (по умолчанию: ┊)
    tool_prefix: "┊"

    # Иконки инструментов: переопределение эмодзи для любого инструмента (используется в спиннерах и прогрессе)
    tool_emojis:
      terminal: "⚔"           # Переопределение эмодзи инструмента terminal
      web_search: "🔮"        # Переопределение эмодзи инструмента web_search
      # Любой инструмент, не указанный здесь, использует значение по умолчанию из реестра

ИСПОЛЬЗОВАНИЕ
=========

.. code-block:: python

    from hermes_cli.skin_engine import get_active_skin, list_skins, set_active_skin

    skin = get_active_skin()
    print(skin.colors["banner_title"])    # "#FFD700"
    print(skin.get_branding("agent_name"))  # "Hermes Agent"

    set_active_skin("ares")               # Переключиться на встроенный скин ares
    set_active_skin("mytheme")            # Переключиться на пользовательский скин из ~/.hermes/skins/

ВСТРОЕННЫЕ СКИНЫ
==============

- ``default`` — Классический Hermes золото/каваии (текущий вид)
- ``ares``    — Малиновый/бронзовый скин бога войны с кастомными крыльями спиннера
- ``mono``    — Чистый монохромный серый
- ``slate``   — Холодный синий скин, ориентированный на разработчиков
- ``daylight`` — Светлая тема с тёмным текстом и синими акцентами
- ``warm-lightmode`` — Тёплый коричневый/золотой текст для светлых фона терминала

ПОЛЬЗОВАТЕЛЬСКИЕ СКИНЫ
======================

Добавьте YAML-файл в ``~/.hermes/skins/<name>.yaml`` согласно схеме выше.
Активируйте командой ``/skin <name>`` в CLI или ``display.skin: <name>`` в config.yaml.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)


# =============================================================================
# Структура данных скина
# =============================================================================

@dataclass
class SkinConfig:
    """Полная конфигурация скина."""
    name: str
    description: str = ""
    colors: Dict[str, str] = field(default_factory=dict)
    spinner: Dict[str, Any] = field(default_factory=dict)
    branding: Dict[str, str] = field(default_factory=dict)
    tool_prefix: str = "┊"
    tool_emojis: Dict[str, str] = field(default_factory=dict)  # переопределения эмодзи для инструментов
    banner_logo: str = ""    # ASCII-арт логотип в разметке Rich (заменяет HERMES_AGENT_LOGO)
    banner_hero: str = ""    # Герой-арт в разметке Rich (заменяет HERMES_CADUCEUS)

    def get_color(self, key: str, fallback: str = "") -> str:
        """Получить значение цвета с фолбэком."""
        return self.colors.get(key, fallback)

    def get_spinner_wings(self) -> List[Tuple[str, str]]:
        """Получить пары крыльев спиннера или пустой список, если нет."""
        raw = self.spinner.get("wings", [])
        result = []
        for pair in raw:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                result.append((str(pair[0]), str(pair[1])))
        return result

    def get_branding(self, key: str, fallback: str = "") -> str:
        """Получить значение брендинга с фолбэком."""
        return self.branding.get(key, fallback)


# =============================================================================
# Определения встроенных скинов
# =============================================================================

_BUILTIN_SKINS: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "default",
        "description": "Классический Hermes — золото и каваии",
        "colors": {
            "banner_border": "#CD7F32",
            "banner_title": "#FFD700",
            "banner_accent": "#FFBF00",
            "banner_dim": "#B8860B",
            "banner_text": "#FFF8DC",
            "ui_accent": "#FFBF00",
            "ui_label": "#DAA520",
            "ui_ok": "#4caf50",
            "ui_error": "#ef5350",
            "ui_warn": "#ffa726",
            "prompt": "#FFF8DC",
            "input_rule": "#CD7F32",
            "response_border": "#FFD700",
            "status_bar_bg": "#1a1a2e",
            "session_label": "#DAA520",
            "session_border": "#8B8682",
        },
        "spinner": {
            # Пусто = использовать захардкоженные значения по умолчанию в display.py
        },
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Добро пожаловать в Hermes Agent! Введите сообщение или /help для команд.",
            "goodbye": "До свидания! ⚕",
            "response_label": " ⚕ Hermes ",
            "prompt_symbol": "❯",
            "help_header": "(^_^)? Доступные команды",
        },
        "tool_prefix": "┊",
    },
    "ares": {
        "name": "ares",
        "description": "Бог войны — малиновый и бронза",
        "colors": {
            "banner_border": "#9F1C1C",
            "banner_title": "#C7A96B",
            "banner_accent": "#DD4A3A",
            "banner_dim": "#6B1717",
            "banner_text": "#F1E6CF",
            "ui_accent": "#DD4A3A",
            "ui_label": "#C7A96B",
            "ui_ok": "#4caf50",
            "ui_error": "#ef5350",
            "ui_warn": "#ffa726",
            "prompt": "#F1E6CF",
            "input_rule": "#9F1C1C",
            "response_border": "#C7A96B",
            "status_bar_bg": "#2A1212",
            "status_bar_text": "#F1E6CF",
            "status_bar_strong": "#C7A96B",
            "status_bar_dim": "#6E584B",
            "status_bar_good": "#7BC96F",
            "status_bar_warn": "#C7A96B",
            "status_bar_bad": "#DD4A3A",
            "status_bar_critical": "#EF5350",
            "session_label": "#C7A96B",
            "session_border": "#6E584B",
        },
        "spinner": {
            "waiting_faces": ["(⚔)", "(⛨)", "(▲)", "(<>)", "(/)"],
            "thinking_faces": ["(⚔)", "(⛨)", "(▲)", "(⌁)", "(<>)"],
            "thinking_verbs": [
                "куёт", "марширует", "оценивает поле", "держит строй",
                "кует планы", "закаляет сталь", "планирует удар", "поднимает щит",
            ],
            "wings": [
                ["⟪⚔", "⚔⟫"],
                ["⟪▲", "▲⟫"],
                ["⟪╸", "╺⟫"],
                ["⟪⛨", "⛨⟫"],
            ],
        },
        "branding": {
            "agent_name": "Ares Agent",
            "welcome": "Добро пожаловать в Ares Agent! Введите сообщение или /help для команд.",
            "goodbye": "Прощай, воин! ⚔",
            "response_label": " ⚔ Ares ",
            "prompt_symbol": "⚔",
            "help_header": "(⚔) Доступные команды",
        },
        "tool_prefix": "╎",
        "banner_logo": """[bold #A3261F] █████╗ ██████╗ ███████╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #B73122]██╔══██╗██╔══██╗██╔════╝██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#C93C24]███████║██████╔╝█████╗  ███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#D84A28]██╔══██║██╔══██╗██╔══╝  ╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#E15A2D]██║  ██║██║  ██║███████╗███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#EB6C32]╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]""",
        "banner_hero": """[#9F1C1C]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#9F1C1C]⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⠟⠻⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#C7A96B]⠀⠀⠀⠀⠀⠀⠀⣠⣾⡿⠋⠀⠀⠀⠙⢿⣷⣄⠀⠀⠀⠀⠀⠀⠀[/]
[#C7A96B]⠀⠀⠀⠀⠀⢀⣾⡿⠋⠀⠀⢠⡄⠀⠀⠙⢿⣷⡀⠀⠀⠀⠀⠀[/]
[#DD4A3A]⠀⠀⠀⠀⣰⣿⠟⠀⠀⠀⣰⣿⣿⣆⠀⠀⠀⠻⣿⣆⠀⠀⠀⠀[/]
[#DD4A3A]⠀⠀⠀⢰⣿⠏⠀⠀⢀⣾⡿⠉⢿⣷⡀⠀⠀⠹⣿⡆⠀⠀⠀[/]
[#9F1C1C]⠀⠀⠀⣿⡟⠀⠀⣠⣿⠟⠀⠀⠀⠻⣿⣄⠀⠀⢻⣿⠀⠀⠀[/]
[#9F1C1C]⠀⠀⠀⣿⡇⠀⠀⠙⠋⠀⠀⚔⠀⠀⠙⠋⠀⠀⢸⣿⠀⠀⠀[/]
[#6B1717]⠀⠀⠀⢿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡿⠀⠀⠀[/]
[#6B1717]⠀⠀⠀⠘⢿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⡿⠃⠀⠀⠀[/]
[#C7A96B]⠀⠀⠀⠀⠈⠻⣿⣷⣦⣤⣀⣀⣤⣤⣶⣿⠿⠋⠀⠀⠀⠀[/]
[#C7A96B]⠀⠀⠀⠀⠀⠀⠀⠉⠛⠿⠿⠿⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀[/]
[#DD4A3A]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⚔⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[dim #6B1717]⠀⠀⠀⠀⠀⠀⠀⠀war god online⠀⠀⠀⠀⠀⠀⠀⠀[/]""",
    },
    "mono": {
        "name": "mono",
        "description": "Монохром — чистые оттенки серого",
        "colors": {
            "banner_border": "#555555",
            "banner_title": "#e6edf3",
            "banner_accent": "#aaaaaa",
            "banner_dim": "#444444",
            "banner_text": "#c9d1d9",
            "ui_accent": "#aaaaaa",
            "ui_label": "#888888",
            "ui_ok": "#888888",
            "ui_error": "#cccccc",
            "ui_warn": "#999999",
            "prompt": "#c9d1d9",
            "input_rule": "#444444",
            "response_border": "#aaaaaa",
            "status_bar_bg": "#1F1F1F",
            "status_bar_text": "#C9D1D9",
            "status_bar_strong": "#E6EDF3",
            "status_bar_dim": "#777777",
            "status_bar_good": "#B5B5B5",
            "status_bar_warn": "#AAAAAA",
            "status_bar_bad": "#D0D0D0",
            "status_bar_critical": "#F0F0F0",
            "session_label": "#888888",
            "session_border": "#555555",
        },
        "spinner": {},
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Добро пожаловать в Hermes Agent! Введите сообщение или /help для команд.",
            "goodbye": "До свидания! ⚕",
            "response_label": " ⚕ Hermes ",
            "prompt_symbol": "❯",
            "help_header": "[?] Доступные команды",
        },
        "tool_prefix": "┊",
    },
    "slate": {
        "name": "slate",
        "description": "Холодный синий — для разработчиков",
        "colors": {
            "banner_border": "#4169e1",
            "banner_title": "#7eb8f6",
            "banner_accent": "#8EA8FF",
            "banner_dim": "#4b5563",
            "banner_text": "#c9d1d9",
            "ui_accent": "#7eb8f6",
            "ui_label": "#8EA8FF",
            "ui_ok": "#63D0A6",
            "ui_error": "#F7A072",
            "ui_warn": "#e6a855",
            "prompt": "#c9d1d9",
            "input_rule": "#4169e1",
            "response_border": "#7eb8f6",
            "status_bar_bg": "#151C2F",
            "status_bar_text": "#C9D1D9",
            "status_bar_strong": "#7EB8F6",
            "status_bar_dim": "#4B5563",
            "status_bar_good": "#63D0A6",
            "status_bar_warn": "#E6A855",
            "status_bar_bad": "#F7A072",
            "status_bar_critical": "#FF7A7A",
            "session_label": "#7eb8f6",
            "session_border": "#4b5563",
        },
        "spinner": {},
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Добро пожаловать в Hermes Agent! Введите сообщение или /help для команд.",
            "goodbye": "До свидания! ⚕",
            "response_label": " ⚕ Hermes ",
            "prompt_symbol": "❯",
            "help_header": "(^_^)? Доступные команды",
        },
        "tool_prefix": "┊",
    },
    "daylight": {
        "name": "daylight",
        "description": "Светлая тема — тёмный текст и синие акценты",
        "colors": {
            "banner_border": "#2563EB",
            "banner_title": "#0F172A",
            "banner_accent": "#1D4ED8",
            "banner_dim": "#475569",
            "banner_text": "#111827",
            "ui_accent": "#2563EB",
            "ui_label": "#0F766E",
            "ui_ok": "#15803D",
            "ui_error": "#B91C1C",
            "ui_warn": "#B45309",
            "prompt": "#111827",
            "input_rule": "#93C5FD",
            "response_border": "#2563EB",
            "session_label": "#1D4ED8",
            "session_border": "#64748B",
            "status_bar_bg": "#E5EDF8",
            "voice_status_bg": "#E5EDF8",
            "completion_menu_bg": "#F8FAFC",
            "completion_menu_current_bg": "#DBEAFE",
            "completion_menu_meta_bg": "#EEF2FF",
            "completion_menu_meta_current_bg": "#BFDBFE",
        },
        "spinner": {},
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Добро пожаловать в Hermes Agent! Введите сообщение или /help для команд.",
            "goodbye": "До свидания! ⚕",
            "response_label": " ⚕ Hermes ",
            "prompt_symbol": "❯",
            "help_header": "[?] Доступные команды",
        },
        "tool_prefix": "│",
    },
    "warm-lightmode": {
        "name": "warm-lightmode",
        "description": "Тёплый светлый режим — тёмный коричневый/золотой текст",
        "colors": {
            "banner_border": "#8B6914",
            "banner_title": "#5C3D11",
            "banner_accent": "#8B4513",
            "banner_dim": "#8B7355",
            "banner_text": "#2C1810",
            "ui_accent": "#8B4513",
            "ui_label": "#5C3D11",
            "ui_ok": "#2E7D32",
            "ui_error": "#C62828",
            "ui_warn": "#E65100",
            "prompt": "#2C1810",
            "input_rule": "#8B6914",
            "response_border": "#8B6914",
            "session_label": "#5C3D11",
            "session_border": "#A0845C",
            "status_bar_bg": "#F5F0E8",
            "voice_status_bg": "#F5F0E8",
            "completion_menu_bg": "#F5EFE0",
            "completion_menu_current_bg": "#E8DCC8",
            "completion_menu_meta_bg": "#F0E8D8",
            "completion_menu_meta_current_bg": "#DFCFB0",
        },
        "spinner": {},
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Добро пожаловать в Hermes Agent! Введите сообщение или /help для команд.",
            "goodbye": "До свидания! ⚕",
            "response_label": " \u2695 Hermes ",
            "prompt_symbol": "\u276f",
            "help_header": "(^_^)? Доступные команды",
        },
        "tool_prefix": "\u250a",
    },
    "poseidon": {
        "name": "poseidon",
        "description": "Бог океана — глубокий синий и морская пена",
        "colors": {
            "banner_border": "#2A6FB9",
            "banner_title": "#A9DFFF",
            "banner_accent": "#5DB8F5",
            "banner_dim": "#153C73",
            "banner_text": "#EAF7FF",
            "ui_accent": "#5DB8F5",
            "ui_label": "#A9DFFF",
            "ui_ok": "#4caf50",
            "ui_error": "#ef5350",
            "ui_warn": "#ffa726",
            "prompt": "#EAF7FF",
            "input_rule": "#2A6FB9",
            "response_border": "#5DB8F5",
            "status_bar_bg": "#0F2440",
            "status_bar_text": "#EAF7FF",
            "status_bar_strong": "#A9DFFF",
            "status_bar_dim": "#496884",
            "status_bar_good": "#6ED7B0",
            "status_bar_warn": "#5DB8F5",
            "status_bar_bad": "#2A6FB9",
            "status_bar_critical": "#D94F4F",
            "session_label": "#A9DFFF",
            "session_border": "#496884",
        },
        "spinner": {
            "waiting_faces": ["(≈)", "(Ψ)", "(∿)", "(◌)", "(◠)"],
            "thinking_faces": ["(Ψ)", "(∿)", "(≈)", "(⌁)", "(◌)"],
            "thinking_verbs": [
                "прокладывает течения", "зондирует глубину", "читает линии пены",
                "правит трезубцем", "отслеживает подтяг", "прокладывает морские пути",
                "вызывает волну", "измеряет давление",
            ],
            "wings": [
                ["⟪≈", "≈⟫"],
                ["⟪Ψ", "Ψ⟫"],
                ["⟪∿", "∿⟫"],
                ["⟪◌", "◌⟫"],
            ],
        },
        "branding": {
            "agent_name": "Poseidon Agent",
            "welcome": "Добро пожаловать в Poseidon Agent! Введите сообщение или /help для команд.",
            "goodbye": "Попутного ветра! Ψ",
            "response_label": " Ψ Poseidon ",
            "prompt_symbol": "Ψ",
            "help_header": "(Ψ) Доступные команды",
        },
        "tool_prefix": "│",
        "banner_logo": """[bold #B8E8FF]██████╗  ██████╗ ███████╗███████╗██╗██████╗  ██████╗ ███╗   ██╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #97D6FF]██╔══██╗██╔═══██╗██╔════╝██╔════╝██║██╔══██╗██╔═══██╗████╗  ██║      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#75C1F6]██████╔╝██║   ██║███████╗█████╗  ██║██║  ██║██║   ██║██╔██╗ ██║█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#4FA2E0]██╔═══╝ ██║   ██║╚════██║██╔══╝  ██║██║  ██║██║   ██║██║╚██╗██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#2E7CC7]██║     ╚██████╔╝███████║███████╗██║██████╔╝╚██████╔╝██║ ╚████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#1B4F95]╚═╝      ╚═════╝ ╚══════╝╚══════╝╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]""",
        "banner_hero": """[#2A6FB9]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#5DB8F5]⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#5DB8F5]⠀⠀⠀⠀⠀⠀⠀⢠⣿⠏⠀Ψ⠀⠹⣿⡄⠀⠀⠀⠀⠀⠀⠀[/]
[#A9DFFF]⠀⠀⠀⠀⠀⠀⠀⣿⡟⠀⠀⠀⠀⠀⢻⣿⠀⠀⠀⠀⠀⠀⠀[/]
[#A9DFFF]⠀⠀⠀≈≈≈≈≈⣿⡇⠀⠀⠀⠀⠀⢸⣿≈≈≈≈≈⠀⠀⠀[/]
[#5DB8F5]⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀[/]
[#2A6FB9]⠀⠀⠀⠀⠀⠀⠀⢿⣧⠀⠀⠀⠀⠀⣼⡿⠀⠀⠀⠀⠀⠀⠀[/]
[#2A6FB9]⠀⠀⠀⠀⠀⠀⠀⠘⢿⣷⣄⣀⣠⣾⡿⠃⠀⠀⠀⠀⠀⠀⠀[/]
[#153C73]⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⡿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#153C73]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#5DB8F5]⠀⠀⠀⠀⠀≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈⠀⠀⠀⠀⠀[/]
[#A9DFFF]⠀⠀⠀⠀⠀⠀≈≈≈≈≈≈≈≈≈≈≈≈≈⠀⠀⠀⠀⠀⠀[/]
[dim #153C73]⠀⠀⠀⠀⠀⠀⠀deep waters hold⠀⠀⠀⠀⠀⠀⠀[/]""",
    },
    "sisyphus": {
        "name": "sisyphus",
        "description": "Сизифова тема — аскетичный серый с упорством",
        "colors": {
            "banner_border": "#B7B7B7",
            "banner_title": "#F5F5F5",
            "banner_accent": "#E7E7E7",
            "banner_dim": "#4A4A4A",
            "banner_text": "#D3D3D3",
            "ui_accent": "#E7E7E7",
            "ui_label": "#D3D3D3",
            "ui_ok": "#919191",
            "ui_error": "#E7E7E7",
            "ui_warn": "#B7B7B7",
            "prompt": "#F5F5F5",
            "input_rule": "#656565",
            "response_border": "#B7B7B7",
            "status_bar_bg": "#202020",
            "status_bar_text": "#D3D3D3",
            "status_bar_strong": "#F5F5F5",
            "status_bar_dim": "#656565",
            "status_bar_good": "#B7B7B7",
            "status_bar_warn": "#D3D3D3",
            "status_bar_bad": "#E7E7E7",
            "status_bar_critical": "#F5F5F5",
            "session_label": "#919191",
            "session_border": "#656565",
        },
        "spinner": {
            "waiting_faces": ["(◉)", "(◌)", "(◬)", "(⬤)", "(::)"],
            "thinking_faces": ["(◉)", "(◬)", "(◌)", "(○)", "(●)"],
            "thinking_verbs": [
                "находит сцепление", "оценивает уклон", "возвращает камень",
                "считает восхождение", "проверяет рычаг", "упирает плечо",
                "толкает в гору", "терпит цикл",
            ],
            "wings": [
                ["⟪◉", "◉⟫"],
                ["⟪◬", "◬⟫"],
                ["⟪◌", "◌⟫"],
                ["⟪⬤", "⬤⟫"],
            ],
        },
        "branding": {
            "agent_name": "Sisyphus Agent",
            "welcome": "Добро пожаловать в Sisyphus Agent! Введите сообщение или /help для команд.",
            "goodbye": "Камень ждёт. ◉",
            "response_label": " ◉ Sisyphus ",
            "prompt_symbol": "◉",
            "help_header": "(◉) Доступные команды",
        },
        "tool_prefix": "│",
        "banner_logo": """[bold #F5F5F5]███████╗██╗███████╗██╗   ██╗██████╗ ██╗  ██╗██╗   ██╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #E7E7E7]██╔════╝██║██╔════╝╚██╗ ██╔╝██╔══██╗██║  ██║██║   ██║██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#D7D7D7]███████╗██║███████╗ ╚████╔╝ ██████╔╝███████║██║   ██║███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#BFBFBF]╚════██║██║╚════██║  ╚██╔╝  ██╔═══╝ ██╔══██║██║   ██║╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#8F8F8F]███████║██║███████║   ██║   ██║     ██║  ██║╚██████╔╝███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#626262]╚══════╝╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]""",
        "banner_hero": """[#B7B7B7]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#D3D3D3]⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#E7E7E7]⠀⠀⠀⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀[/]
[#F5F5F5]⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀[/]
[#E7E7E7]⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀[/]
[#D3D3D3]⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⠀⠀[/]
[#B7B7B7]⠀⠀⠀⠀⠀⠀⠀⠀⠙⠿⣿⠿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#919191]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#656565]⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#656565]⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#4A4A4A]⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#4A4A4A]⠀⠀⠀⠀⠀⣀⣴⣿⣿⣿⣿⣿⣿⣦⣀⠀⠀⠀⠀⠀⠀[/]
[#656565]⠀⠀⠀━━━━━━━━━━━━━━━━━━━━━━━⠀⠀⠀[/]
[dim #4A4A4A]⠀⠀⠀⠀⠀⠀⠀⠀⠀the boulder⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]""",
    },
    "charizard": {
        "name": "charizard",
        "description": "Вулканическая тема — жжёный оранжевый и уголёк",
        "colors": {
            "banner_border": "#C75B1D",
            "banner_title": "#FFD39A",
            "banner_accent": "#F29C38",
            "banner_dim": "#7A3511",
            "banner_text": "#FFF0D4",
            "ui_accent": "#F29C38",
            "ui_label": "#FFD39A",
            "ui_ok": "#4caf50",
            "ui_error": "#ef5350",
            "ui_warn": "#ffa726",
            "prompt": "#FFF0D4",
            "input_rule": "#C75B1D",
            "response_border": "#F29C38",
            "status_bar_bg": "#2B160E",
            "status_bar_text": "#FFF0D4",
            "status_bar_strong": "#FFD39A",
            "status_bar_dim": "#6C4724",
            "status_bar_good": "#6BCB77",
            "status_bar_warn": "#F29C38",
            "status_bar_bad": "#E2832B",
            "status_bar_critical": "#EF5350",
            "session_label": "#FFD39A",
            "session_border": "#6C4724",
        },
        "spinner": {
            "waiting_faces": ["(✦)", "(▲)", "(◇)", "(<>)", "(🔥)"],
            "thinking_faces": ["(✦)", "(▲)", "(◇)", "(⌁)", "(🔥)"],
            "thinking_verbs": [
                "входит в поток", "измеряет жар", "читает восходящий поток",
                "отслеживает падение углей", "устанавливает угол крыла", "держит ядро пламени",
                "планирует горячую посадку", "сворачивается для подъёма",
            ],
            "wings": [
                ["⟪✦", "✦⟫"],
                ["⟪▲", "▲⟫"],
                ["⟪◌", "◌⟫"],
                ["⟪◇", "◇⟫"],
            ],
        },
        "branding": {
            "agent_name": "Charizard Agent",
            "welcome": "Добро пожаловать в Charizard Agent! Введите сообщение или /help для команд.",
            "goodbye": "Гасну! ✦",
            "response_label": " ✦ Charizard ",
            "prompt_symbol": "✦",
            "help_header": "(✦) Доступные команды",
        },
        "tool_prefix": "│",
        "banner_logo": """[bold #FFF0D4] ██████╗██╗  ██╗ █████╗ ██████╗ ██╗███████╗ █████╗ ██████╗ ██████╗        █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD39A]██╔════╝██║  ██║██╔══██╗██╔══██╗██║╚══███╔╝██╔══██╗██╔══██╗██╔══██╗      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#F29C38]██║     ███████║███████║██████╔╝██║  ███╔╝ ███████║██████╔╝██║  ██║█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#E2832B]██║     ██╔══██║██╔══██║██╔══██╗██║ ███╔╝  ██╔══██║██╔══██╗██║  ██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#C75B1D]╚██████╗██║  ██║██║  ██║██║  ██║██║███████╗██║  ██║██║  ██║██████╔╝      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#7A3511] ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝       ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]""",
        "banner_hero": """[#FFD39A]⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠶⠶⠶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#F29C38]⠀⠀⠀⠀⠀⠀⣴⠟⠁⠀⠀⠀⠀⠈⠻⣦⠀⠀⠀⠀⠀⠀[/]
[#F29C38]⠀⠀⠀⠀⠀⣼⠏⠀⠀⠀✦⠀⠀⠀⠀⠹⣧⠀⠀⠀⠀⠀[/]
[#E2832B]⠀⠀⠀⠀⢰⡟⠀⠀⣀⣤⣤⣤⣀⠀⠀⠀⢻⡆⠀⠀⠀⠀[/]
[#E2832B]⠀⠀⣠⡾⠛⠁⣠⣾⠟⠉⠀⠉⠻⣷⣄⠀⠈⠛⢷⣄⠀⠀[/]
[#C75B1D]⠀⣼⠟⠀⢀⣾⠟⠁⠀⠀⠀⠀⠀⠈⠻⣷⡀⠀⠻⣧⠀[/]
[#C75B1D]⢸⡟⠀⠀⣿⡟⠀⠀⠀🔥⠀⠀⠀⠀⢻⣿⠀⠀⢻⡇[/]
[#7A3511]⠀⠻⣦⡀⠘⢿⣧⡀⠀⠀⠀⠀⠀⢀⣼⡿⠃⢀⣴⠟⠀[/]
[#7A3511]⠀⠀⠈⠻⣦⣀⠙⢿⣷⣤⣤⣤⣾⡿⠋⣀⣴⠟⠁⠀⠀[/]
[#C75B1D]⠀⠀⠀⠀⠈⠙⠛⠶⠤⠭⠭⠤⠶⠛⠋⠁⠀⠀⠀⠀[/]
[#F29C38]⠀⠀⠀⠀⠀⠀⠀⠀⣰⡿⢿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#F29C38]⠀⠀⠀⠀⠀⠀⠀⣼⡟⠀⠀⢻⣧⠀⠀⠀⠀⠀⠀⠀⠀[/]
[dim #7A3511]⠀⠀⠀⠀⠀⠀⠀tail flame lit⠀⠀⠀⠀⠀⠀⠀⠀[/]""",
    },
}


# =============================================================================
# Загрузка и управление скинами
# =============================================================================

_active_skin: Optional[SkinConfig] = None
_active_skin_name: str = "default"


def _skins_dir() -> Path:
    """Директория пользовательских скинов."""
    return get_hermes_home() / "skins"


def _load_skin_from_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Загрузить определение скина из YAML-файла."""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "name" in data:
            return data
    except Exception as e:
        logger.debug("Failed to load skin from %s: %s", path, e)
    return None


def _mapping_or_empty(value: Any, *, section: str, skin_name: str) -> Dict[str, Any]:
    """Вернуть значение mapping или пустой dict, если тип секции невалиден."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    logger.warning(
        "Скин '%s' имеет невалидный тип секции '%s' (%s); игнорирую секцию",
        skin_name,
        section,
        type(value).__name__,
    )
    return {}


def _build_skin_config(data: Dict[str, Any]) -> SkinConfig:
    """Построить SkinConfig из сырого dict (встроенный или загруженный из YAML)."""
    # Начать со значений по умолчанию как базы для отсутствующих ключей
    default = _BUILTIN_SKINS["default"]
    skin_name = str(data.get("name", "unknown"))
    color_overrides = _mapping_or_empty(data.get("colors"), section="colors", skin_name=skin_name)
    spinner_overrides = _mapping_or_empty(data.get("spinner"), section="spinner", skin_name=skin_name)
    branding_overrides = _mapping_or_empty(data.get("branding"), section="branding", skin_name=skin_name)
    emoji_overrides = _mapping_or_empty(data.get("tool_emojis"), section="tool_emojis", skin_name=skin_name)

    colors = dict(default.get("colors", {}))
    colors.update(color_overrides)
    spinner = dict(default.get("spinner", {}))
    spinner.update(spinner_overrides)
    branding = dict(default.get("branding", {}))
    branding.update(branding_overrides)

    return SkinConfig(
        name=skin_name,
        description=data.get("description", ""),
        colors=colors,
        spinner=spinner,
        branding=branding,
        tool_prefix=data.get("tool_prefix", default.get("tool_prefix", "┊")),
        tool_emojis=emoji_overrides,
        banner_logo=data.get("banner_logo", ""),
        banner_hero=data.get("banner_hero", ""),
    )


def list_skins() -> List[Dict[str, str]]:
    """Вернуть список всех доступных скинов (встроенные + пользовательские).

    Возвращает список {"name": ..., "description": ..., "source": "builtin"|"user"}.
    """
    result = []
    for name, data in _BUILTIN_SKINS.items():
        result.append({
            "name": name,
            "description": data.get("description", ""),
            "source": "builtin",
        })

    skins_path = _skins_dir()
    if skins_path.is_dir():
        for f in sorted(skins_path.glob("*.yaml")):
            data = _load_skin_from_yaml(f)
            if data:
                skin_name = data.get("name", f.stem)
                # Пропустить, если он затеняет встроенный
                if any(s["name"] == skin_name for s in result):
                    continue
                result.append({
                    "name": skin_name,
                    "description": data.get("description", ""),
                    "source": "user",
                })

    return result


def load_skin(name: str) -> SkinConfig:
    """Загрузить скин по имени. Сначала проверяет пользовательские, затем встроенные."""
    # Проверить пользовательские скины
    skins_path = _skins_dir()
    user_file = skins_path / f"{name}.yaml"
    if user_file.is_file():
        data = _load_skin_from_yaml(user_file)
        if data:
            return _build_skin_config(data)

    # Проверить встроенные скины
    if name in _BUILTIN_SKINS:
        return _build_skin_config(_BUILTIN_SKINS[name])

    # Фолбэк на default
    logger.warning("Skin '%s' not found, using default", name)
    return _build_skin_config(_BUILTIN_SKINS["default"])


def get_active_skin() -> SkinConfig:
    """Получить конфигурацию текущего активного скина (кэшированная)."""
    global _active_skin
    if _active_skin is None:
        _active_skin = load_skin(_active_skin_name)
    return _active_skin


def set_active_skin(name: str) -> SkinConfig:
    """Переключить активный скин. Возвращает новый SkinConfig."""
    global _active_skin, _active_skin_name
    _active_skin_name = name
    _active_skin = load_skin(name)
    return _active_skin


def get_active_skin_name() -> str:
    """Получить имя текущего активного скина."""
    return _active_skin_name


def init_skin_from_config(config: dict) -> None:
    """Инициализировать активный скин из CLI-конфига при запуске.

    Вызвать один раз во время инициализации CLI с загруженным dict конфига.
    """
    display = config.get("display") or {}
    if not isinstance(display, dict):
        display = {}
    skin_name = display.get("skin", "default")
    if isinstance(skin_name, str) and skin_name.strip():
        set_active_skin(skin_name.strip())
    else:
        set_active_skin("default")


# =============================================================================
# Удобные хелперы для CLI-модулей
# =============================================================================


def get_active_prompt_symbol(fallback: str = "❯") -> str:
    """Возвращает символ интерактивного приглашения с одним пробелом в конце.

    Скины хранят ``prompt_symbol`` как голый токен (без пробелов). Пробел в конце
    добавляется здесь, чтобы вызывающие могли использовать его прямо в рендеринге
    приглашения без ручного добавления пробела.
    """
    try:
        raw = get_active_skin().get_branding("prompt_symbol", fallback)
    except Exception:
        raw = fallback

    cleaned = (raw or fallback).strip()

    return f"{cleaned or fallback.strip()} "



def get_active_help_header(fallback: str = "(^_^)? Доступные команды") -> str:
    """Получить заголовок /help из активного скина."""
    try:
        return get_active_skin().get_branding("help_header", fallback)
    except Exception:
        return fallback



def get_active_goodbye(fallback: str = "До свидания! ⚕") -> str:
    """Получить строку прощания из активного скина."""
    try:
        return get_active_skin().get_branding("goodbye", fallback)
    except Exception:
        return fallback



def get_prompt_toolkit_style_overrides() -> Dict[str, str]:
    """Возвращает переопределения стилей prompt_toolkit на основе активного скина.

    Они накладываются поверх базового стиля TUI CLI, поэтому /skin может обновить
    живой интерфейс prompt_toolkit немедленно без пересоздания приложения.
    """
    try:
        skin = get_active_skin()
    except Exception:
        return {}

    # Ввод/приглашение: не задано по умолчанию, чтобы вводимый текст наследовал
    # цвет переднего плана терминала (читается и в светлых, и в тёмных схемах).
    # Скины могут явно задать цветной prompt в своём YAML.
    prompt = skin.get_color("prompt", "")
    input_rule = skin.get_color("input_rule", "#CD7F32")
    title = skin.get_color("banner_title", "#FFD700")
    text = skin.get_color("banner_text", "#FFF8DC")
    dim = skin.get_color("banner_dim", "#555555")
    label = skin.get_color("ui_label", title)
    warn = skin.get_color("ui_warn", "#FF8C00")
    error = skin.get_color("ui_error", "#FF6B6B")
    status_bg = skin.get_color("status_bar_bg", "#1a1a2e")
    status_text = skin.get_color("status_bar_text", text)
    status_strong = skin.get_color("status_bar_strong", title)
    status_dim = skin.get_color("status_bar_dim", dim)
    status_good = skin.get_color("status_bar_good", skin.get_color("ui_ok", "#8FBC8F"))
    status_warn = skin.get_color("status_bar_warn", warn)
    status_bad = skin.get_color("status_bar_bad", skin.get_color("banner_accent", warn))
    status_critical = skin.get_color("status_bar_critical", error)
    voice_bg = skin.get_color("voice_status_bg", status_bg)
    menu_bg = skin.get_color("completion_menu_bg", "#1a1a2e")
    menu_current_bg = skin.get_color("completion_menu_current_bg", "#333355")
    menu_meta_bg = skin.get_color("completion_menu_meta_bg", menu_bg)
    menu_meta_current_bg = skin.get_color("completion_menu_meta_current_bg", menu_current_bg)

    return {
        # Вводимый текст всегда использует стандартные fg/bg терминала, чтобы
        # читаться и в светлых, и в тёмлых режимах Terminal.app.
        # `prompt` цвет скина (если есть) стилизует только символ приглашения,
        # а НЕ вводимый пользователем текст.
        "input-area": "",
        "placeholder": f"{dim} italic",
        "prompt": prompt,
        "prompt-working": f"{dim} italic",
        "hint": f"{dim} italic",
        "status-bar": f"bg:{status_bg} {status_text}",
        "status-bar-strong": f"bg:{status_bg} {status_strong} bold",
        "status-bar-dim": f"bg:{status_bg} {status_dim}",
        "status-bar-good": f"bg:{status_bg} {status_good} bold",
        "status-bar-warn": f"bg:{status_bg} {status_warn} bold",
        "status-bar-bad": f"bg:{status_bg} {status_bad} bold",
        "status-bar-critical": f"bg:{status_bg} {status_critical} bold",
        "input-rule": input_rule,
        "image-badge": f"{label} bold",
        "completion-menu": f"bg:{menu_bg} {text}",
        "completion-menu.completion": f"bg:{menu_bg} {text}",
        "completion-menu.completion.current": f"bg:{menu_current_bg} {title}",
        "completion-menu.meta.completion": f"bg:{menu_meta_bg} {dim}",
        "completion-menu.meta.completion.current": f"bg:{menu_meta_current_bg} {label}",
        "clarify-border": input_rule,
        "clarify-title": f"{title} bold",
        "clarify-question": f"{text} bold",
        "clarify-choice": dim,
        "clarify-selected": f"{title} bold",
        "clarify-active-other": f"{title} italic",
        "clarify-countdown": input_rule,
        "sudo-prompt": f"{error} bold",
        "sudo-border": input_rule,
        "sudo-title": f"{error} bold",
        "sudo-text": text,
        "approval-border": input_rule,
        "approval-title": f"{warn} bold",
        "approval-desc": f"{text} bold",
        "approval-cmd": f"{dim} italic",
        "approval-choice": dim,
        "approval-selected": f"{title} bold",
        "voice-status": f"bg:{voice_bg} {label}",
        "voice-status-recording": f"bg:{voice_bg} {error} bold",
    }
