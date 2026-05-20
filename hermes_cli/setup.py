"""
Интерактивный мастер настройки для Hermes Agent.

Модульный мастер с независимо запускаемыми секциями:
  1. Модель и провайдер — выберите ваш AI провайдер и модель
  2. Терминальный бэкенд — где ваш агент выполняет команды
  3. Настройки агента — итерации, сжатие, сброс сессии
  4. Платформы сообщений — подключите Telegram, Discord и т.д.
  5. Инструменты — настройте TTS, веб-поиск, генерацию изображений и т.д.

Файлы конфигурации хранятся в ~/.hermes/ для удобного доступа.
"""

# IMPORTANT: hermes_bootstrap must be imported first for Windows UTF-8 support
try:
    import hermes_bootstrap  # noqa: F401
except ModuleNotFoundError:
    pass

import importlib.util
import json
import logging
import os
import re
import shutil
import sys
import copy
from pathlib import Path
from typing import Optional, Dict, Any

from hermes_cli.nous_subscription import get_nous_subscription_features
from tools.tool_backend_helpers import managed_nous_tools_enabled
from utils import base_url_hostname
from hermes_constants import get_optional_skills_dir

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

_DOCS_BASE = "https://hermes-agent.nousresearch.com/docs"


def _model_config_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    current_model = config.get("model")
    if isinstance(current_model, dict):
        return dict(current_model)
    if isinstance(current_model, str) and current_model.strip():
        return {"default": current_model.strip()}
    return {}


def _get_credential_pool_strategies(config: Dict[str, Any]) -> Dict[str, str]:
    strategies = config.get("credential_pool_strategies")
    return dict(strategies) if isinstance(strategies, dict) else {}


def _set_credential_pool_strategy(config: Dict[str, Any], provider: str, strategy: str) -> None:
    if not provider:
        return
    strategies = _get_credential_pool_strategies(config)
    strategies[provider] = strategy
    config["credential_pool_strategies"] = strategies


def _supports_same_provider_pool_setup(provider: str) -> bool:
    if not provider or provider == "custom":
        return False
    if provider == "openrouter":
        return True
    from hermes_cli.auth import PROVIDER_REGISTRY

    pconfig = PROVIDER_REGISTRY.get(provider)
    if not pconfig:
        return False
    return pconfig.auth_type in {"api_key", "oauth_device_code"}


# Default model lists per provider — used as fallback when the live
# /models endpoint can't be reached.
_DEFAULT_PROVIDER_MODELS = {
    "copilot-acp": [
        "copilot-acp",
    ],
    "copilot": [
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5-mini",
        "gpt-5.3-codex",
        "gpt-5.2-codex",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-opus-4.6",
        "claude-sonnet-4.6",
        "claude-sonnet-4.5",
        "claude-haiku-4.5",
        "gemini-2.5-pro",
    ],
    "gemini": [
        "gemini-3.1-pro-preview", "gemini-3-pro-preview",
        "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview",
    ],
    "zai": ["glm-5.1", "glm-5", "glm-4.7", "glm-4.5", "glm-4.5-flash"],
    "kimi-coding": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-turbo-preview"],
    "kimi-coding-cn": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-turbo-preview"],
    "stepfun": ["step-3.5-flash", "step-3.5-flash-2603"],
    "arcee": ["trinity-large-thinking", "trinity-large-preview", "trinity-mini"],
    "minimax": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"],
    "minimax-cn": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"],
    "ai-gateway": ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6", "openai/gpt-5", "google/gemini-3-flash"],
    "kilocode": ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6", "openai/gpt-5.4", "google/gemini-3-pro-preview", "google/gemini-3-flash-preview"],
    "opencode-zen": ["gpt-5.4", "gpt-5.3-codex", "claude-sonnet-4-6", "gemini-3-flash", "glm-5", "kimi-k2.5", "minimax-m2.7"],
    "opencode-go": ["kimi-k2.6", "kimi-k2.5", "glm-5.1", "glm-5", "mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-pro", "mimo-v2-omni", "minimax-m2.7", "minimax-m2.5", "qwen3.6-plus", "qwen3.5-plus"],
    "huggingface": [
        "Qwen/Qwen3.5-397B-A17B", "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "Qwen/Qwen3-Coder-480B-A35B-Instruct", "deepseek-ai/DeepSeek-R1-0528",
        "deepseek-ai/DeepSeek-V3.2", "moonshotai/Kimi-K2.5",
    ],
}


def _current_reasoning_effort(config: Dict[str, Any]) -> str:
    agent_cfg = config.get("agent")
    if isinstance(agent_cfg, dict):
        return str(agent_cfg.get("reasoning_effort") or "").strip().lower()
    return ""


def _set_reasoning_effort(config: Dict[str, Any], effort: str) -> None:
    agent_cfg = config.get("agent")
    if not isinstance(agent_cfg, dict):
        agent_cfg = {}
        config["agent"] = agent_cfg
    agent_cfg["reasoning_effort"] = effort




# Import config helpers
from hermes_cli.config import (
    cfg_get,
    DEFAULT_CONFIG,
    get_hermes_home,
    get_config_path,
    get_env_path,
    load_config,
    save_config,
    save_env_value,
    remove_env_value,
    get_env_value,
    ensure_hermes_home,
)
# display_hermes_home imported lazily at call sites (stale-module safety during hermes update)

from hermes_cli.colors import Colors, color


def print_header(title: str):
    """Вывести заголовок секции."""
    print()
    print(color(f"◆ {title}", Colors.CYAN, Colors.BOLD))


from hermes_cli.cli_output import (  # noqa: E402
    print_error,
    print_info,
    print_success,
    print_warning,
)


def is_interactive_stdin() -> bool:
    """Вернуть True когда stdin выглядит как интерактивный TTY."""
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except Exception:
        return False


def print_noninteractive_setup_guidance(reason: str | None = None) -> None:
    """Вывести инструкции для headless/неинтерактивных режимов настройки."""
    print()
    print(color("⚕ Hermes Setup — Неинтерактивный режим", Colors.CYAN, Colors.BOLD))
    print()
    if reason:
        print_info(reason)
    print_info("Интерактивный мастер не может быть использован здесь.")
    print()
    print_info("Настройте Hermes через переменные окружения или команды конфигурации:")
    print_info("  hermes config set model.provider custom")
    print_info("  hermes config set model.base_url http://localhost:8080/v1")
    print_info("  hermes config set model.default имя-модели")
    print()
    print_info("Или установите OPENROUTER_API_KEY / OPENAI_API_KEY в окружение.")
    print_info("Запустите 'hermes setup' в интерактивном терминале для полного мастера.")
    print()


def prompt(question: str, default: str = None, password: bool = False) -> str:
    """Запрос ввода с опциональным значением по умолчанию."""
    if default:
        display = f"{question} [{default}]: "
    else:
        display = f"{question}: "

    try:
        if password:
            import getpass

            value = getpass.getpass(color(display, Colors.YELLOW))
        else:
            value = input(color(display, Colors.YELLOW))

        cleaned = _sanitize_pasted_input(value)
        return cleaned.strip() or default or ""
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(1)


_BRACKETED_PASTE_PATTERN = re.compile(r"\x1b\[\s*200~|\x1b\[\s*201~")


def _sanitize_pasted_input(value: str) -> str:
    """Удалить терминальные control-маркеры bracketed-paste из вставленного текста."""
    if not isinstance(value, str) or not value:
        return value
    return _BRACKETED_PASTE_PATTERN.sub("", value)


def _curses_prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int:
    """Меню одиночного выбора используя curses. Делегирует curses_radiolist."""
    from hermes_cli.curses_ui import curses_radiolist
    return curses_radiolist(question, choices, selected=default, cancel_returns=-1, description=description)



def prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int:
    """Запрос выбора из списка с навигацией стрелками.

    Escape сохраняет текущее значение по умолчанию (пропускает вопрос).
    Ctrl+C выходит из мастера.
    """
    idx = _curses_prompt_choice(question, choices, default, description=description)
    if idx >= 0:
        if idx == default:
            print_info("  Пропущено (сохраняется текущее)")
            print()
            return default
        print()
        return idx

    print(color(question, Colors.YELLOW))
    for i, choice in enumerate(choices):
        marker = "●" if i == default else "○"
        if i == default:
            print(color(f"  {marker} {choice}", Colors.GREEN))
        else:
            print(f"  {marker} {choice}")

    print_info(f"  Enter для выбора по умолчанию ({default + 1})  Ctrl+C для выхода")

    while True:
        try:
            value = input(
                color(f"  Выберите [1-{len(choices)}] ({default + 1}): ", Colors.DIM)
            )
            if not value:
                return default
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return idx
            print_error(f"Введите число от 1 до {len(choices)}")
        except ValueError:
            print_error("Введите число")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Запрос yes/no. Ctrl+C выходит, пустой ввод возвращает значение по умолчанию."""
    default_str = "Y/n" if default else "y/N"

    while True:
        try:
            value = (
                input(color(f"{question} [{default_str}]: ", Colors.YELLOW))
                .strip()
                .lower()
            )
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)

        if not value:
            return default
        if value in {"y", "yes", "да", "д"}:
            return True
        if value in {"n", "no", "нет", "н"}:
            return False
        print_error("Введите 'y' или 'n'")


def prompt_checklist(title: str, items: list, pre_selected: list = None) -> list:
    """
    Отобразить многоэлементный список выбора и вернуть индексы выбранных элементов.

    Каждый элемент в `items` — это строка отображения. `pre_selected` — это список
    индексов, которые должны быть отмечены по умолчанию. Опция "Продолжить →" 
    добавляется в конце — пользователь переключает элементы через Space и подтверждает
    через Enter на "Продолжить →".

    Использует простой интерфейс с номерами когда simple_term_menu недоступен.

    Возвращает:
        Список выбранных индексов (не включая опцию Continue).
    """
    if pre_selected is None:
        pre_selected = []

    from hermes_cli.curses_ui import curses_checklist

    chosen = curses_checklist(
        title,
        items,
        set(pre_selected),
        cancel_returns=set(pre_selected),
    )
    return sorted(chosen)


def _prompt_api_key(var: dict):
    """Отобразить красивый ввод API ключа для одной переменной окружения."""
    tools = var.get("tools", [])
    tools_str = ", ".join(tools[:3])
    if len(tools) > 3:
        tools_str += f", +{len(tools) - 3} ещё"

    print()
    print(color(f"  ─── {var.get('description', var['name'])} ───", Colors.CYAN))
    print()
    if tools_str:
        print_info(f"  Включает: {tools_str}")
    if var.get("url"):
        print_info(f"  Получить ключ на: {var['url']}")
    print()

    if var.get("password"):
        value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
    else:
        value = prompt(f"  {var.get('prompt', var['name'])}")

    if value:
        save_env_value(var["name"], value)
        print_success("  ✓ Сохранено")
    else:
        print_warning("  Пропущено (настройте позже через 'hermes setup')")


def _print_setup_summary(config: dict, hermes_home):
    """Вывести сводку завершения настройки."""
    # Tool availability summary
    print()
    print_header("Сводка доступности инструментов")

    tool_status = []
    subscription_features = get_nous_subscription_features(config)

    # Vision — use the same runtime resolver as the actual vision tools
    try:
        from agent.auxiliary_client import get_available_vision_backends

        _vision_backends = get_available_vision_backends()
    except Exception:
        _vision_backends = []

    if _vision_backends:
        tool_status.append(("Видение (анализ изображений)", True, None))
    else:
        tool_status.append(("Видение (анализ изображений)", False, "запустите 'hermes setup' для настройки"))

    # Mixture of Agents — requires OpenRouter specifically (calls multiple models)
    if get_env_value("OPENROUTER_API_KEY"):
        tool_status.append(("Mixture of Agents", True, None))
    else:
        tool_status.append(("Mixture of Agents", False, "OPENROUTER_API_KEY"))

    # Web tools (Exa, Parallel, Firecrawl, or Tavily)
    if subscription_features.web.managed_by_nous:
        tool_status.append(("Веб-поиск и извлечение (подписка Nous)", True, None))
    elif subscription_features.web.available:
        label = "Веб-поиск и извлечение"
        if subscription_features.web.current_provider:
            label = f"Веб-поиск и извлечение ({subscription_features.web.current_provider})"
        tool_status.append((label, True, None))
    else:
        tool_status.append(("Веб-поиск и извлечение", False, "EXA_API_KEY, PARALLEL_API_KEY, FIRECRAWL_API_KEY/FIRECRAWL_API_URL, TAVILY_API_KEY, или SEARXNG_URL"))

    # Browser tools (local Chromium, Camofox, Browserbase, Browser Use, or Firecrawl)
    browser_provider = subscription_features.browser.current_provider
    if subscription_features.browser.managed_by_nous:
        tool_status.append(("Автоматизация браузера (Nous Browser Use)", True, None))
    elif subscription_features.browser.available:
        label = "Автоматизация браузера"
        if browser_provider:
            label = f"Автоматизация браузера ({browser_provider})"
        tool_status.append((label, True, None))
    else:
        missing_browser_hint = "npm install -g agent-browser, установите CAMOFOX_URL, или настройте Browser Use или Browserbase"
        if browser_provider == "Browserbase":
            missing_browser_hint = (
                "npm install -g agent-browser и установите "
                "BROWSERBASE_API_KEY/BROWSERBASE_PROJECT_ID"
            )
        elif browser_provider == "Browser Use":
            missing_browser_hint = (
                "npm install -g agent-browser и установите BROWSER_USE_API_KEY"
            )
        elif browser_provider == "Camofox":
            missing_browser_hint = "CAMOFOX_URL"
        elif browser_provider == "Local browser":
            missing_browser_hint = "npm install -g agent-browser"
        tool_status.append(
            ("Автоматизация браузера", False, missing_browser_hint)
        )

    # Image generation — FAL (direct or via Nous), or any plugin-registered
    # provider (OpenAI, etc.)
    if subscription_features.image_gen.managed_by_nous:
        tool_status.append(("Генерация изображений (подписка Nous)", True, None))
    elif subscription_features.image_gen.available:
        tool_status.append(("Генерация изображений", True, None))
    else:
        # Fall back to probing plugin-registered providers so OpenAI-only
        # setups don't show as "missing FAL_KEY".
        _img_backend = None
        try:
            from agent.image_gen_registry import list_providers
            from hermes_cli.plugins import _ensure_plugins_discovered

            _ensure_plugins_discovered()
            for _p in list_providers():
                if _p.name == "fal":
                    continue
                try:
                    if _p.is_available():
                        _img_backend = _p.display_name
                        break
                except Exception:
                    continue
        except Exception:
            pass
        if _img_backend:
            tool_status.append((f"Генерация изображений ({_img_backend})", True, None))
        else:
            tool_status.append(("Генерация изображений", False, "FAL_KEY или OPENAI_API_KEY"))

    # Video generation — opt-in via `hermes tools` → Video Generation.
    # Only show the row when a plugin reports available so we don't badger
    # users who don't care about video gen with a "missing" status line.
    try:
        from agent.video_gen_registry import list_providers as _list_video_providers
        from hermes_cli.plugins import _ensure_plugins_discovered as _ensure_plugins
        _ensure_plugins()
        _video_backend = None
        for _vp in _list_video_providers():
            try:
                if _vp.is_available():
                    _video_backend = _vp.display_name
                    break
            except Exception:
                continue
    except Exception:
        _video_backend = None
    if _video_backend:
        tool_status.append((f"Генерация видео ({_video_backend})", True, None))

    # TTS — show configured provider
    tts_provider = cfg_get(config, "tts", "provider", default="edge")
    if subscription_features.tts.managed_by_nous:
        tool_status.append(("Синтез речи (OpenAI через подписку Nous)", True, None))
    elif tts_provider == "elevenlabs" and get_env_value("ELEVENLABS_API_KEY"):
        tool_status.append(("Синтез речи (ElevenLabs)", True, None))
    elif tts_provider == "openai" and (
        get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY")
    ):
        tool_status.append(("Синтез речи (OpenAI)", True, None))
    elif tts_provider == "minimax" and get_env_value("MINIMAX_API_KEY"):
        tool_status.append(("Синтез речи (MiniMax)", True, None))
    elif tts_provider == "mistral" and get_env_value("MISTRAL_API_KEY"):
        tool_status.append(("Синтез речи (Mistral Voxtral)", True, None))
    elif tts_provider == "gemini" and (get_env_value("GEMINI_API_KEY") or get_env_value("GOOGLE_API_KEY")):
        tool_status.append(("Синтез речи (Google Gemini)", True, None))
    elif tts_provider == "neutts":
        try:
            neutts_ok = importlib.util.find_spec("neutts") is not None
        except Exception:
            neutts_ok = False
        if neutts_ok:
            tool_status.append(("Синтез речи (NeuTTS локально)", True, None))
        else:
            tool_status.append(("Синтез речи (NeuTTS — не установлен)", False, "запустите 'hermes setup tts'"))
    elif tts_provider == "kittentts":
        try:
            import importlib.util
            kittentts_ok = importlib.util.find_spec("kittentts") is not None
        except Exception:
            kittentts_ok = False
        if kittentts_ok:
            tool_status.append(("Синтез речи (KittenTTS локально)", True, None))
        else:
            tool_status.append(("Синтез речи (KittenTTS — не установлен)", False, "запустите 'hermes setup tts'"))
    else:
        tool_status.append(("Синтез речи (Edge TTS)", True, None))

    if subscription_features.modal.managed_by_nous:
        tool_status.append(("Выполнение Modal (подписка Nous)", True, None))
    elif cfg_get(config, "terminal", "backend") == "modal":
        if subscription_features.modal.direct_override:
            tool_status.append(("Выполнение Modal (прямое подключение Modal)", True, None))
        else:
            tool_status.append(("Выполнение Modal", False, "запустите 'hermes setup terminal'"))
    elif managed_nous_tools_enabled() and subscription_features.nous_auth_present:
        tool_status.append(("Выполнение Modal (опционально через подписку Nous)", True, None))

    # Home Assistant
    if get_env_value("HASS_TOKEN"):
        tool_status.append(("Умный дом (Home Assistant)", True, None))

    # Spotify (OAuth через hermes auth spotify — проверяем auth.json, не env vars)
    try:
        from hermes_cli.auth import get_provider_auth_state
        _spotify_state = get_provider_auth_state("spotify") or {}
        if _spotify_state.get("access_token") or _spotify_state.get("refresh_token"):
            tool_status.append(("Spotify (PKCE OAuth)", True, None))
    except Exception:
        pass

    # Skills Hub
    if get_env_value("GITHUB_TOKEN"):
        tool_status.append(("Хаб навыков (GitHub)", True, None))
    else:
        tool_status.append(("Хаб навыков (GitHub)", False, "GITHUB_TOKEN"))

    # Terminal (always available if system deps met)
    tool_status.append(("Терминал/Команды", True, None))

    # Task planning (always available, in-memory)
    tool_status.append(("Планирование задач (todo)", True, None))

    # Skills (always available -- bundled skills + user-created skills)
    tool_status.append(("Навыки (просмотр, создание, редактирование)", True, None))

    # Print status
    available_count = sum(1 for _, avail, _ in tool_status if avail)
    total_count = len(tool_status)

    print_info(f"{available_count}/{total_count} категорий инструментов доступно:")
    print()

    for name, available, missing_var in tool_status:
        if available:
            print(f"   {color('✓', Colors.GREEN)} {name}")
        else:
            print(
                f"   {color('✗', Colors.RED)} {name} {color(f'(отсутствует {missing_var})', Colors.DIM)}"
            )

    print()

    disabled_tools = [(name, var) for name, avail, var in tool_status if not avail]
    if disabled_tools:
        print_warning(
            "Некоторые инструменты отключены. Запустите 'hermes setup tools' для настройки,"
        )
        from hermes_constants import display_hermes_home as _dhh
        print_warning(f"или отредактируйте {_dhh()}/.env напрямую чтобы добавить отсутствующие API ключи.")
        print()

    # Done banner
    print()
    print(
        color(
            "┌─────────────────────────────────────────────────────────┐", Colors.GREEN
        )
    )
    print(
        color(
            "│              ✓ Настройка завершена!                     │", Colors.GREEN
        )
    )
    print(
        color(
            "└─────────────────────────────────────────────────────────┘", Colors.GREEN
        )
    )
    print()

    # Show file locations prominently
    from hermes_constants import display_hermes_home as _dhh
    print(color(f"📁 Все ваши файлы в {_dhh()}/:", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('Настройки:', Colors.YELLOW)}  {get_config_path()}")
    print(f"   {color('API ключи:', Colors.YELLOW)}  {get_env_path()}")
    print(
        f"   {color('Данные:', Colors.YELLOW)}      {hermes_home}/cron/, sessions/, logs/"
    )
    print()

    print(color("─" * 60, Colors.DIM))
    print()
    print(color("📝 Для редактирования конфигурации:", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('hermes setup', Colors.GREEN)}          Запустить полный мастер заново")
    print(f"   {color('hermes setup model', Colors.GREEN)}    Изменить модель/провайдер")
    print(f"   {color('hermes setup terminal', Colors.GREEN)} Изменить терминальный бэкенд")
    print(f"   {color('hermes setup gateway', Colors.GREEN)}  Настроить сообщения")
    print(f"   {color('hermes setup tools', Colors.GREEN)}    Настроить провайдеры инструментов")
    print()
    print(f"   {color('hermes config', Colors.GREEN)}         Просмотр текущих настроек")
    print(
        f"   {color('hermes config edit', Colors.GREEN)}    Открыть конфиг в редакторе"
    )
    print(f"   {color('hermes config set <key> <value>', Colors.GREEN)}")
    print("                          Установить конкретное значение")
    print()
    print("   Или отредактируйте файлы напрямую:")
    print(f"   {color(f'nano {get_config_path()}', Colors.DIM)}")
    print(f"   {color(f'nano {get_env_path()}', Colors.DIM)}")
    print()

    print(color("─" * 60, Colors.DIM))
    print()
    print(color("🚀 Готово к работе!", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('hermes', Colors.GREEN)}              Начать разговор")
    print(f"   {color('hermes gateway', Colors.GREEN)}      Запустить шлюз сообщений")
    print(f"   {color('hermes doctor', Colors.GREEN)}       Проверить проблемы")
    print()


def _prompt_container_resources(config: dict):
    """Запрос настроек ресурсов контейнера (Docker, Singularity, Modal, Daytona)."""
    terminal = config.setdefault("terminal", {})

    print()
    print_info("Настройки ресурсов контейнера:")

    # Persistence
    current_persist = terminal.get("container_persistent", True)
    persist_label = "да" if current_persist else "нет"
    print_info("  Постоянная файловая система сохраняет файлы между сессиями.")
    print_info("  Установите 'нет' для эфемерных песочниц, которые сбрасываются каждый раз.")
    persist_str = prompt(
        "  Сохранять файловую систему между сессиями? (да/нет)", persist_label
    )
    terminal["container_persistent"] = persist_str.lower() in {"да", "yes", "true", "y", "1", "д"}

    # CPU
    current_cpu = terminal.get("container_cpu", 1)
    cpu_str = prompt("  Ядра CPU", str(current_cpu))
    try:
        terminal["container_cpu"] = float(cpu_str)
    except ValueError:
        pass

    # Memory
    current_mem = terminal.get("container_memory", 5120)
    mem_str = prompt("  Память в МБ (5120 = 5ГБ)", str(current_mem))
    try:
        terminal["container_memory"] = int(mem_str)
    except ValueError:
        pass

    # Disk
    current_disk = terminal.get("container_disk", 51200)
    disk_str = prompt("  Диск в МБ (51200 = 50ГБ)", str(current_disk))
    try:
        terminal["container_disk"] = int(disk_str)
    except ValueError:
        pass


def _prompt_vercel_sandbox_settings(config: dict):
    """Запрос настроек Vercel Sandbox без неподдерживаемого размера диска."""
    terminal = config.setdefault("terminal", {})

    print()
    print_info("Настройки Vercel Sandbox:")
    print_info("  Постоянство файловой системы использует снимки Vercel.")
    print_info("  Снимки восстанавливают только файлы; живые процессы не продолжаются после воссоздания песочницы.")

    from tools.terminal_tool import _SUPPORTED_VERCEL_RUNTIMES

    current_runtime = terminal.get("vercel_runtime") or "node24"
    supported_label = ", ".join(_SUPPORTED_VERCEL_RUNTIMES)
    runtime = prompt(f"  Runtime ({supported_label})", current_runtime).strip() or current_runtime
    if runtime not in _SUPPORTED_VERCEL_RUNTIMES:
        print_warning(f"Неподдерживаемый Vercel runtime '{runtime}', сохраняем {current_runtime}.")
        runtime = current_runtime if current_runtime in _SUPPORTED_VERCEL_RUNTIMES else "node24"
    terminal["vercel_runtime"] = runtime
    save_env_value("TERMINAL_VERCEL_RUNTIME", runtime)

    current_persist = terminal.get("container_persistent", True)
    persist_label = "да" if current_persist else "нет"
    terminal["container_persistent"] = prompt(
        "  Сохранять файловую систему со снимками? (да/нет)", persist_label
    ).lower() in {"да", "yes", "true", "y", "1", "д"}

    current_cpu = terminal.get("container_cpu", 1)
    cpu_str = prompt("  Ядра CPU", str(current_cpu))
    try:
        terminal["container_cpu"] = float(cpu_str)
    except ValueError:
        pass

    current_mem = terminal.get("container_memory", 5120)
    mem_str = prompt("  Память в МБ (5120 = 5ГБ)", str(current_mem))
    try:
        terminal["container_memory"] = int(mem_str)
    except ValueError:
        pass

    if terminal.get("container_disk", 51200) not in {0, 51200}:
        print_warning("Vercel Sandbox не поддерживает настройку диска; сбрасываем container_disk на 51200.")
    terminal["container_disk"] = 51200

    print()
    print_info("Аутентификация Vercel:")
    print_info("  Используйте долгоживущий токен доступа Vercel плюс ID проекта/команды.")
    linked_project = _read_nearest_vercel_project()
    if linked_project:
        print_info("  Найдены значения по умолчанию в ближайшем .vercel/project.json.")

    remove_env_value("VERCEL_OIDC_TOKEN")
    token = prompt("    Токен доступа Vercel", get_env_value("VERCEL_TOKEN") or "", password=True)
    project = prompt(
        "    ID проекта Vercel",
        get_env_value("VERCEL_PROJECT_ID") or linked_project.get("projectId", ""),
    )
    team = prompt(
        "    Vercel team ID",
        get_env_value("VERCEL_TEAM_ID") or linked_project.get("orgId", ""),
    )
    if token:
        save_env_value("VERCEL_TOKEN", token)
    if project:
        save_env_value("VERCEL_PROJECT_ID", project)
    if team:
        save_env_value("VERCEL_TEAM_ID", team)


def _read_nearest_vercel_project(start: Path | None = None) -> dict[str, str]:
    """Read project/team defaults from the nearest Vercel link file."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        project_file = directory / ".vercel" / "project.json"
        if not project_file.exists():
            continue
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            key: value
            for key, value in {
                "projectId": data.get("projectId"),
                "orgId": data.get("orgId"),
            }.items()
            if isinstance(value, str) and value.strip()
        }
    return {}


# Tool categories and provider config are now in tools_config.py (shared
# between `hermes tools` and `hermes setup tools`).


# =============================================================================
# Section 1: Model & Provider Configuration
# =============================================================================



def setup_model_provider(config: dict, *, quick: bool = False):
    """Настроить провайдера инференса и модель по умолчанию.

    Делегирует ``cmd_model()`` (тот же поток что используется в ``hermes model``)
    для выбора провайдера, запроса учётных данных и выбора модели.
    Это обеспечивает единый код для всей настройки провайдера — любой новый
    провайдер добавленный в ``hermes model`` автоматически доступен здесь.

    Когда *quick* True, пропускает ротацию учётных данных, видение и TTS
    конфигурацию — используется для оптимизированной первоначальной быстрой настройки.
    """
    from hermes_cli.config import load_config, save_config

    print_header("Провайдер инференса")
    print_info("Выберите как подключиться к вашей основной чат-модели.")
    print_info(f"   Руководство: {_DOCS_BASE}/integrations/providers")
    print()

    # Delegate to the shared hermes model flow — handles provider picker,
    # credential prompting, model selection, and config persistence.
    from hermes_cli.main import select_provider_and_model
    try:
        select_provider_and_model()
    except (SystemExit, KeyboardInterrupt):
        print()
        print_info("Настройка провайдера пропущена.")
    except Exception as exc:
        logger.debug("Ошибка select_provider_and_model во время настройки: %s", exc)
        print_warning(f"Настройка провайдера завершилась ошибкой: {exc}")
        print_info("Вы можете попробовать позже через: hermes model")

    # Re-sync the wizard's config dict from what cmd_model saved to disk.
    # This is critical: cmd_model writes to disk via its own load/save cycle,
    # and the wizard's final save_config(config) must not overwrite those
    # changes with stale values (#4172).
    # Повторная синхронизация конфига мастера с тем что cmd_model сохранил на диск.
    # Это критично: cmd_model пишет на диск через свой собственный цикл загрузки/сохранения,
    # и финальный save_config(config) мастера не должен перезаписывать это
    # устаревшими значениями (#4172).
    _refreshed = load_config()
    config["model"] = _refreshed.get("model", config.get("model"))
    if "custom_providers" in _refreshed:
        config["custom_providers"] = _refreshed["custom_providers"]
    else:
        config.pop("custom_providers", None)

    # Выводим выбранного провайдера для последующих шагов (настройка видения).
    selected_provider = None
    _m = config.get("model")
    if isinstance(_m, dict):
        selected_provider = _m.get("provider")

    # ── Настройка резервного провайдера и ротации (только полная настройка) ──
    if not quick and _supports_same_provider_pool_setup(selected_provider):
        try:
            from types import SimpleNamespace
            from agent.credential_pool import load_pool
            from hermes_cli.auth_commands import auth_add_command

            pool = load_pool(selected_provider)
            entries = pool.entries()
            entry_count = len(entries)
            manual_count = sum(1 for entry in entries if str(getattr(entry, "source", "")).startswith("manual"))
            auto_count = entry_count - manual_count
            print()
            print_header("Резервный провайдер и ротация")
            print_info(
                "Hermes может хранить несколько учётных данных для одного провайдера и ротировать между"
            )
            print_info(
                "ними когда учётные данные исчерпаны или rate-limited. Это сохраняет"
            )
            print_info(
                "вашего основного провайдера одновременно уменьшая прерывания от проблем с квотой."
            )
            print()
            if auto_count > 0:
                print_info(
                    f"Текущие объединённые учётные данные для {selected_provider}: {entry_count} "
                    f"({manual_count} ручных, {auto_count} авто-обнаружено из env/shared auth)"
                )
            else:
                print_info(f"Текущие объединённые учётные данные для {selected_provider}: {entry_count}")

            while prompt_yes_no("Добавить другую учётную запись для резервного варианта того же провайдера?", False):
                auth_add_command(
                    SimpleNamespace(
                        provider=selected_provider,
                        auth_type="",
                        label=None,
                        api_key=None,
                        portal_url=None,
                        inference_url=None,
                        client_id=None,
                        scope=None,
                        no_browser=False,
                        timeout=15.0,
                        insecure=False,
                        ca_bundle=None,
                        min_key_ttl_seconds=5 * 60,
                    )
                )
                pool = load_pool(selected_provider)
                entry_count = len(pool.entries())
                print_info(f"Пул провайдера теперь имеет {entry_count} учётную(ые) запись(и).")

            if entry_count > 1:
                strategy_labels = [
                    "Fill-first / sticky — продолжать использовать первую здоровую учётную запись пока не исчерпана",
                    "Round robin — ротация к следующей здоровой учётной записи после каждого выбора",
                    "Random — выбор случайной здоровой учётной записи каждый раз",
                ]
                current_strategy = _get_credential_pool_strategies(config).get(selected_provider, "fill_first")
                default_strategy_idx = {
                    "fill_first": 0,
                    "round_robin": 1,
                    "random": 2,
                }.get(current_strategy, 0)
                strategy_idx = prompt_choice(
                    "Выберите стратегию ротации того же провайдера:",
                    strategy_labels,
                    default_strategy_idx,
                )
                strategy_value = ["fill_first", "round_robin", "random"][strategy_idx]
                _set_credential_pool_strategy(config, selected_provider, strategy_value)
                print_success(f"Сохранена стратегия ротации {selected_provider}: {strategy_value}")
        except Exception as exc:
            logger.debug("Не удалось настроить резервный вариант того же провайдера в настройке: %s", exc)

    # ── Настройка видения и анализа изображений (только полная настройка) ──
    if quick:
        _vision_needs_setup = False
    else:
        try:
            from agent.auxiliary_client import get_available_vision_backends
            _vision_backends = set(get_available_vision_backends())
        except Exception:
            _vision_backends = set()

        _vision_needs_setup = not bool(_vision_backends)

        if selected_provider in _vision_backends:
            _vision_needs_setup = False

    if _vision_needs_setup:
        _prov_names = {
            "nous-api": "Nous Portal API ключ",
            "copilot": "GitHub Copilot",
            "copilot-acp": "GitHub Copilot ACP",
            "zai": "Z.AI / GLM",
            "kimi-coding": "Kimi / Moonshot",
            "kimi-coding-cn": "Kimi / Moonshot (Китай)",
            "stepfun": "StepFun Step Plan",
            "minimax": "MiniMax",
            "minimax-cn": "MiniMax CN",
            "anthropic": "Anthropic",
            "ai-gateway": "Vercel AI Gateway",
            "custom": "ваш кастомный эндпоинт",
        }
        _prov_display = _prov_names.get(selected_provider, selected_provider or "выбранный провайдер")

        print()
        print_header("Видение и анализ изображений (опционально)")
        print_info(f"Видение использует отдельный мультимодальный бэкенд. {_prov_display}")
        print_info("сейчас не предоставляет один который Hermes может авто-использовать для видения,")
        print_info("поэтому выберите бэкенд сейчас или пропустите и настройте позже.")
        print()

        _vision_choices = [
            "OpenRouter — использует Gemini (бесплатный тариф на openrouter.ai/keys)",
            "OpenAI-совместимый эндпоинт — base URL, API ключ и модель видения",
            "Пропустить сейчас",
        ]
        _vision_idx = prompt_choice("Настроить видение:", _vision_choices, 2)

        if _vision_idx == 0:  # OpenRouter
            _or_key = prompt("  API ключ OpenRouter", password=True).strip()
            if _or_key:
                save_env_value("OPENROUTER_API_KEY", _or_key)
                print_success("Ключ OpenRouter сохранён — видение будет использовать Gemini")
            else:
                print_info("Пропущено — видение не будет доступно")
        elif _vision_idx == 1:  # OpenAI-compatible endpoint
            _base_url = prompt("  Base URL (пусто для OpenAI)").strip() or "https://api.openai.com/v1"
            _api_key_label = "  API ключ"
            _is_native_openai = base_url_hostname(_base_url) == "api.openai.com"
            if _is_native_openai:
                _api_key_label = "  API ключ OpenAI"
            _oai_key = prompt(_api_key_label, password=True).strip()
            if _oai_key:
                save_env_value("OPENAI_API_KEY", _oai_key)
                # Сохраняем vision base URL в config (не в .env — только секреты идут туда)
                _vaux = config.setdefault("auxiliary", {}).setdefault("vision", {})
                _vaux["base_url"] = _base_url
                if _is_native_openai:
                    _oai_vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
                    _vm_choices = _oai_vision_models + ["Использовать по умолчанию (gpt-4o-mini)"]
                    _vm_idx = prompt_choice("Выберите модель видения:", _vm_choices, 0)
                    _selected_vision_model = (
                        _oai_vision_models[_vm_idx]
                        if _vm_idx < len(_oai_vision_models)
                        else "gpt-4o-mini"
                    )
                else:
                    _selected_vision_model = prompt("  Модель видения (пусто = использовать основную/кастомную по умолчанию)").strip()
                if _selected_vision_model:
                    save_env_value("AUXILIARY_VISION_MODEL", _selected_vision_model)
                print_success(
                    f"Видение настроено с {_base_url}"
                    + (f" ({_selected_vision_model})" if _selected_vision_model else "")
                )
            else:
                print_info("Пропущено — видение не будет доступно")
        else:
            print_info("Пропущено — добавьте позже через 'hermes setup' или настройте AUXILIARY_VISION_*")


    # Подсказка Tool Gateway уже показана через _model_flow_nous() выше.
    save_config(config)

    if not quick and selected_provider != "nous":
        _setup_tts_provider(config)


# =============================================================================
# Раздел 1b: Настройка TTS провайдера
# =============================================================================


def _check_espeak_ng() -> bool:
    """Проверить установлен ли espeak-ng."""
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def _install_neutts_deps() -> bool:
    """Установить зависимости NeuTTS с одобрения пользователя. Возвращает True при успехе."""
    import subprocess
    import sys

    # Проверка espeak-ng
    if not _check_espeak_ng():
        print()
        print_warning("NeuTTS требует espeak-ng для фонемизации.")
        if sys.platform == "darwin":
            print_info("Установите: brew install espeak-ng")
        elif sys.platform == "win32":
            print_info("Установите: choco install espeak-ng")
        else:
            print_info("Установите: sudo apt install espeak-ng")
        print()
        if prompt_yes_no("Установить espeak-ng сейчас?", True):
            try:
                if sys.platform == "darwin":
                    subprocess.run(["brew", "install", "espeak-ng"], check=True)
                elif sys.platform == "win32":
                    subprocess.run(["choco", "install", "espeak-ng", "-y"], check=True)
                else:
                    subprocess.run(["sudo", "apt", "install", "-y", "espeak-ng"], check=True)
                print_success("espeak-ng установлен")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print_warning(f"Не удалось установить espeak-ng автоматически: {e}")
                print_info("Пожалуйста, установите его вручную и перезапустите настройку.")
                return False
        else:
            print_warning("espeak-ng требуется для NeuTTS. Установите его вручную перед использованием NeuTTS.")

    # Установка Python пакета neutts
    print()
    print_info("Установка Python пакета neutts...")
    print_info("Это также загрузит TTS модель (~300MB) при первом использовании.")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "neutts[all]", "--quiet"],
            check=True, timeout=300,
        )
        print_success("neutts успешно установлен")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"Не удалось установить neutts: {e}")
        print_info("Попробуйте вручную: python -m pip install -U neutts[all]")
        return False


def _install_kittentts_deps() -> bool:
    """Установить зависимости KittenTTS с одобрения пользователя. Возвращает True при успехе."""
    import subprocess
    import sys

    wheel_url = (
        "https://github.com/KittenML/KittenTTS/releases/download/"
        "0.8.1/kittentts-0.8.1-py3-none-any.whl"
    )
    print()
    print_info("Установка Python пакета kittentts (~25-80MB модель загружается при первом использовании)...")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", wheel_url, "soundfile", "--quiet"],
            check=True, timeout=300,
        )
        print_success("kittentts успешно установлен")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"Не удалось установить kittentts: {e}")
        print_info(f"Попробуйте вручную: python -m pip install -U '{wheel_url}' soundfile")
        return False


def _xai_oauth_logged_in_for_setup() -> bool:
    """True если учётные данные xAI Grok OAuth уже сохранены локально.

    Позволяет настройке TTS / STT пропустить запрос API ключа для пользователей которые вошли
    через ``hermes model`` -> xAI Grok OAuth (подписка SuperGrok).
    """
    try:
        from hermes_cli.auth import get_xai_oauth_auth_status

        return bool(get_xai_oauth_auth_status().get("logged_in"))
    except Exception:
        return False


def _run_xai_oauth_login_from_setup() -> bool:
    """Запустить логин xAI Grok OAuth loopback изнутри мастера настройки.

    Возвращает True при успехе, False при любой ошибке (вызывающий возвращается
    к тому что пользователь выбрал следующим, например Edge TTS).
    """
    try:
        from hermes_cli.auth import (
            DEFAULT_XAI_OAUTH_BASE_URL,
            _is_remote_session,
            _save_xai_oauth_tokens,
            _update_config_for_provider,
            _xai_oauth_loopback_login,
        )
    except Exception as exc:
        print_warning(f"xAI Grok OAuth helpers unavailable: {exc}")
        return False

    open_browser = not _is_remote_session()
    print()
    print_info("Вход в xAI Grok OAuth (подписка SuperGrok)...")
    try:
        creds = _xai_oauth_loopback_login(open_browser=open_browser)
        _save_xai_oauth_tokens(
            creds["tokens"],
            discovery=creds.get("discovery"),
            redirect_uri=creds.get("redirect_uri", ""),
            last_refresh=creds.get("last_refresh"),
        )
        _update_config_for_provider(
            "xai-oauth", creds.get("base_url", DEFAULT_XAI_OAUTH_BASE_URL)
        )
        return True
    except Exception as exc:
        print_warning(f"Вход xAI Grok OAuth не удался: {exc}")
        return False


def _setup_tts_provider(config: dict):
    """Интерактивный выбор TTS провайдера с потоком установки для NeuTTS."""
    tts_config = config.get("tts", {})
    current_provider = tts_config.get("provider", "edge")
    subscription_features = get_nous_subscription_features(config)

    provider_labels = {
        "edge": "Edge TTS",
        "elevenlabs": "ElevenLabs",
        "openai": "OpenAI TTS",
        "xai": "xAI TTS",
        "minimax": "MiniMax TTS",
        "mistral": "Mistral Voxtral TTS",
        "gemini": "Google Gemini TTS",
        "neutts": "NeuTTS",
        "kittentts": "KittenTTS",
    }
    current_label = provider_labels.get(current_provider, current_provider)

    print()
    print_header("Провайдер Text-to-Speech (опционально)")
    print_info(f"Текущий: {current_label}")
    print()

    choices = []
    providers = []
    if managed_nous_tools_enabled() and subscription_features.nous_auth_present:
        choices.append("Подписка Nous (управляемый OpenAI TTS, оплата по подписке)")
        providers.append("nous-openai")
    choices.extend(
        [
            "Edge TTS (бесплатно, облачный, не требует настройки)",
            "ElevenLabs (премиум качество, нужен API ключ)",
            "OpenAI TTS (хорошее качество, нужен API ключ)",
            "xAI TTS (голоса Grok — вход через OAuth или API ключ)",
            "MiniMax TTS (высокое качество с клонированием голоса, нужен API ключ)",
            "Mistral Voxtral TTS (многоязычный, родной Opus, нужен API ключ)",
            "Google Gemini TTS (30 встроенных голосов, управляемый промптом, нужен API ключ)",
            "NeuTTS (локальный на устройстве, бесплатно, ~300MB загрузка модели)",
            "KittenTTS (локальный на устройстве, бесплатно, легковесный ~25-80MB ONNX)",
        ]
    )
    providers.extend(["edge", "elevenlabs", "openai", "xai", "minimax", "mistral", "gemini", "neutts", "kittentts"])
    choices.append(f"Сохранить текущий ({current_label})")
    keep_current_idx = len(choices) - 1
    idx = prompt_choice("Выберите TTS провайдера:", choices, keep_current_idx)

    if idx == keep_current_idx:
        return

    selected = providers[idx]
    selected_via_nous = selected == "nous-openai"
    if selected == "nous-openai":
        selected = "openai"
        print_info("OpenAI TTS будет использовать управляемый шлюз Nous и списывать средства с вашей подписки.")
        if get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY"):
            print_warning(
                "Прямые учётные данные OpenAI всё ещё настроены и могут иметь приоритет пока не удалены из ~/.hermes/.env."
            )

    if selected == "neutts":
        # Проверка уже установлен
        try:
            already_installed = importlib.util.find_spec("neutts") is not None
        except Exception:
            already_installed = False

        if already_installed:
            print_success("NeuTTS уже установлен")
        else:
            print()
            print_info("NeuTTS требует:")
            print_info("  • Python пакет: neutts (~50MB установка + ~300MB модель при первом использовании)")
            print_info("  • Системный пакет: espeak-ng (фонемизатор)")
            print()
            if prompt_yes_no("Установить зависимости NeuTTS сейчас?", True):
                if not _install_neutts_deps():
                    print_warning("Установка NeuTTS не завершена. Возвращаемся к Edge TTS.")
                    selected = "edge"
            else:
                print_info("Пропускаем установку. Установите tts.provider в 'neutts' после ручной установки.")
                selected = "edge"

    elif selected == "elevenlabs":
        existing = get_env_value("ELEVENLABS_API_KEY")
        if not existing:
            print()
            api_key = prompt("API ключ ElevenLabs", password=True)
            if api_key:
                save_env_value("ELEVENLABS_API_KEY", api_key)
                print_success("API ключ ElevenLabs сохранён")
            else:
                print_warning("API ключ не предоставлен. Возвращаемся к Edge TTS.")
                selected = "edge"

    elif selected == "openai" and not selected_via_nous:
        existing = get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY")
        if not existing:
            print()
            api_key = prompt("API ключ OpenAI для TTS", password=True)
            if api_key:
                save_env_value("VOICE_TOOLS_OPENAI_KEY", api_key)
                print_success("API ключ OpenAI TTS сохранён")
            else:
                print_warning("API ключ не предоставлен. Возвращаемся к Edge TTS.")
                selected = "edge"

    elif selected == "xai":
        # Порядок разрешения: существующие OAuth токены (бесплатно для подписчиков SuperGrok
        # через Hermes auth store) > существующий XAI_API_KEY > запрос пользователя.
        # Когда ни одно не настроено, предлагаем оба варианта вместо принуждения
        # пути API ключа — xAI TTS хорошо работает с OAuth bearer токенами тоже.
        oauth_logged_in = _xai_oauth_logged_in_for_setup()
        existing_api_key = get_env_value("XAI_API_KEY")

        if oauth_logged_in:
            print_success(
                "xAI TTS будет использовать ваши учётные данные xAI Grok OAuth (подписка SuperGrok)"
            )
        elif existing_api_key:
            print_success("xAI TTS будет использовать ваш существующий XAI_API_KEY")
        else:
            print()
            choice_idx = prompt_choice(
                "Как вы хотите аутентифицироваться для xAI TTS?",
                choices=[
                    "Войти через xAI Grok OAuth (подписка SuperGrok) — вход через браузер",
                    "Вставить API ключ xAI (console.x.ai)",
                    "Пропустить → вернуться к Edge TTS",
                ],
                default=0,
            )
            if choice_idx == 0:
                if _run_xai_oauth_login_from_setup():
                    print_success("Выполнен вход — xAI TTS будет использовать эти OAuth учётные данные")
                else:
                    print_warning("Вход xAI Grok OAuth не завершён. Возвращаемся к Edge TTS.")
                    selected = "edge"
            elif choice_idx == 1:
                api_key = prompt("API ключ xAI для TTS", password=True)
                if api_key:
                    save_env_value("XAI_API_KEY", api_key)
                    print_success("API ключ xAI TTS сохранён")
                else:
                    from hermes_constants import display_hermes_home as _dhh
                    print_warning(
                        "API ключ xAI для TTS не предоставлен. Настройте XAI_API_KEY "
                        f"через hermes setup model или {_dhh()}/.env для использования xAI TTS. "
                        "Возвращаемся к Edge TTS."
                    )
                    selected = "edge"
            else:
                print_warning("xAI TTS пропущен. Возвращаемся к Edge TTS.")
                selected = "edge"

        if selected == "xai":
            print()
            voice_id = prompt("voice_id xAI (Enter для 'eve', или вставьте ID кастомного голоса)")
            if voice_id and voice_id.strip():
                config.setdefault("tts", {}).setdefault("xai", {})["voice_id"] = voice_id.strip()
                print_success(f"xAI voice_id установлен в: {voice_id.strip()}")


    elif selected == "minimax":
        existing = get_env_value("MINIMAX_API_KEY")
        if not existing:
            print()
            api_key = prompt("API ключ MiniMax для TTS", password=True)
            if api_key:
                save_env_value("MINIMAX_API_KEY", api_key)
                print_success("API ключ MiniMax TTS сохранён")
            else:
                print_warning("API ключ не предоставлен. Возвращаемся к Edge TTS.")
                selected = "edge"

    elif selected == "mistral":
        existing = get_env_value("MISTRAL_API_KEY")
        if not existing:
            print()
            api_key = prompt("API ключ Mistral для TTS", password=True)
            if api_key:
                save_env_value("MISTRAL_API_KEY", api_key)
                print_success("API ключ Mistral TTS сохранён")
            else:
                print_warning("API ключ не предоставлен. Возвращаемся к Edge TTS.")
                selected = "edge"

    elif selected == "gemini":
        existing = get_env_value("GEMINI_API_KEY") or get_env_value("GOOGLE_API_KEY")
        if not existing:
            print()
            print_info("Получите бесплатный API ключ на https://aistudio.google.com/app/apikey")
            api_key = prompt("API ключ Gemini для TTS", password=True)
            if api_key:
                save_env_value("GEMINI_API_KEY", api_key)
                print_success("API ключ Gemini TTS сохранён")
            else:
                print_warning("API ключ не предоставлен. Возвращаемся к Edge TTS.")
                selected = "edge"

    elif selected == "kittentts":
        # Проверка уже установлен
        try:
            import importlib.util
            already_installed = importlib.util.find_spec("kittentts") is not None
        except Exception:
            already_installed = False

        if already_installed:
            print_success("KittenTTS уже установлен")
        else:
            print()
            print_info("KittenTTS легковесный (~25-80MB, только CPU, не требуется API ключ).")
            print_info("Голоса: Jasper, Bella, Luna, Bruno, Rosie, Hugo, Kiki, Leo")
            print()
            if prompt_yes_no("Установить KittenTTS сейчас?", True):
                if not _install_kittentts_deps():
                    print_warning("Установка KittenTTS не завершена. Возвращаемся к Edge TTS.")
                    selected = "edge"
            else:
                print_info("Пропускаем установку. Установите tts.provider в 'kittentts' после ручной установки.")
                selected = "edge"

    # Save the selection
    if "tts" not in config:
        config["tts"] = {}
    config["tts"]["provider"] = selected
    save_config(config)
    print_success(f"TTS provider set to: {provider_labels.get(selected, selected)}")


def setup_tts(config: dict):
    """Standalone TTS setup (for 'hermes setup tts')."""
    _setup_tts_provider(config)


# =============================================================================
# Section 2: Terminal Backend Configuration
# =============================================================================


def setup_terminal_backend(config: dict):
    """Настроить терминальный бэкенд выполнения."""
    import platform as _platform
    print_header("Терминальный бэкенд")
    print_info("Выберите где Hermes выполняет shell команды и код.")
    print_info("Это влияет на выполнение инструментов, доступ к файлам и изоляцию.")
    print_info(f"   Руководство: {_DOCS_BASE}/developer-guide/environments")
    print()

    current_backend = cfg_get(config, "terminal", "backend", default="local")
    is_linux = _platform.system() == "Linux"

    # Build backend choices with descriptions
    terminal_choices = [
        "Локально — запускать непосредственно на этой машине (по умолчанию)",
        "Docker — изолированный контейнер с настраиваемыми ресурсами",
        "Modal — serverless облачная песочница",
        "SSH — запуск на удалённой машине",
        "Daytona — постоянная облачная среда разработки",
        "Vercel Sandbox — облачная микроВМ с постоянством снимков файловой системы",
    ]
    idx_to_backend = {0: "local", 1: "docker", 2: "modal", 3: "ssh", 4: "daytona", 5: "vercel_sandbox"}
    backend_to_idx = {"local": 0, "docker": 1, "modal": 2, "ssh": 3, "daytona": 4, "vercel_sandbox": 5}

    next_idx = 6
    if is_linux:
        terminal_choices.append("Singularity/Apptainer — контейнер для HPC")
        idx_to_backend[next_idx] = "singularity"
        backend_to_idx["singularity"] = next_idx
        next_idx += 1

    # Add keep current option
    keep_current_idx = next_idx
    terminal_choices.append(f"Сохранить текущий ({current_backend})")
    idx_to_backend[keep_current_idx] = current_backend

    terminal_idx = prompt_choice(
        "Выберите терминальный бэкенд:", terminal_choices, keep_current_idx
    )

    selected_backend = idx_to_backend.get(terminal_idx)

    if terminal_idx == keep_current_idx:
        print_info(f"Сохраняем текущий бэкенд: {current_backend}")
        return

    config.setdefault("terminal", {})["backend"] = selected_backend

    if selected_backend == "local":
        print_success("Терминальный бэкенд: Локальный")
        print_info("Команды выполняются непосредственно на этой машине.")

        # Gateway/cron working directory
        print()
        print_info("Рабочий каталог шлюза:")
        print_info("  Используется сессиями Telegram/Discord/cron.")
        print_info("  CLI/TUI всегда использует каталог запуска вместо этого.")
        current_cwd = cfg_get(config, "terminal", "cwd", default="")
        cwd = prompt("  Рабочий каталог шлюза", current_cwd or str(Path.home()))
        if cwd:
            config["terminal"]["cwd"] = cwd

        # Sudo support
        print()
        existing_sudo = get_env_value("SUDO_PASSWORD")
        if existing_sudo:
            print_info("Пароль sudo: настроен")
        elif prompt_yes_no(
            "Включить поддержку sudo? (сохраняет пароль для apt install и т.д.)", False
        ):
            sudo_pass = prompt("  Пароль sudo", password=True)
            if sudo_pass:
                save_env_value("SUDO_PASSWORD", sudo_pass)
                print_success("Пароль sudo сохранён")

    elif selected_backend == "docker":
        print_success("Терминальный бэкенд: Docker")

        # Check if Docker is available
        docker_bin = shutil.which("docker")
        if not docker_bin:
            print_warning("Docker не найден в PATH!")
            print_info("Установите Docker: https://docs.docker.com/get-docker/")
        else:
            print_info(f"Docker found: {docker_bin}")

        # Docker image
        current_image = cfg_get(config, "terminal", "docker_image", default="nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  Docker image", current_image)
        config["terminal"]["docker_image"] = image
        save_env_value("TERMINAL_DOCKER_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "singularity":
        print_success("Терминальный бэкенд: Singularity/Apptainer")

        # Check if singularity/apptainer is available
        sing_bin = shutil.which("apptainer") or shutil.which("singularity")
        if not sing_bin:
            print_warning("Singularity/Apptainer не найден в PATH!")
            print_info(
                "Установка: https://apptainer.org/docs/admin/main/installation.html"
            )
        else:
            print_info(f"Найдено: {sing_bin}")

        current_image = cfg_get(config, "terminal", "singularity_image", default="docker://nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  Образ контейнера", current_image)
        config["terminal"]["singularity_image"] = image
        save_env_value("TERMINAL_SINGULARITY_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "modal":
        print_success("Терминальный бэкенд: Modal")
        print_info("Serverless облачные песочницы. Каждая сессия получает свой собственный контейнер.")
        from tools.managed_tool_gateway import is_managed_tool_gateway_ready
        from tools.tool_backend_helpers import normalize_modal_mode

        managed_modal_available = bool(
            managed_nous_tools_enabled()
            and
            get_nous_subscription_features(config).nous_auth_present
            and is_managed_tool_gateway_ready("modal")
        )
        modal_mode = normalize_modal_mode(cfg_get(config, "terminal", "modal_mode"))
        use_managed_modal = False
        if managed_modal_available:
            modal_choices = [
                "Use my Nous subscription",
                "Use my own Modal account",
            ]
            if modal_mode == "managed":
                default_modal_idx = 0
            elif modal_mode == "direct":
                default_modal_idx = 1
            else:
                default_modal_idx = 1 if get_env_value("MODAL_TOKEN_ID") else 0
            modal_mode_idx = prompt_choice(
                "Select how Modal execution should be billed:",
                modal_choices,
                default_modal_idx,
            )
            use_managed_modal = modal_mode_idx == 0

        if use_managed_modal:
            config["terminal"]["modal_mode"] = "managed"
            print_info("Выполнение Modal будет использовать управляемый шлюз Nous и списывать средства с вашей подписки.")
            if get_env_value("MODAL_TOKEN_ID") or get_env_value("MODAL_TOKEN_SECRET"):
                print_info(
                    "Direct Modal credentials are still configured, but this backend is pinned to managed mode."
                )
        else:
            config["terminal"]["modal_mode"] = "direct"
            print_info("Требуется аккаунт Modal: https://modal.com")

            # Check if modal SDK is installed
            try:
                __import__("modal")
            except ImportError:
                print_info("Установка modal SDK...")
                import subprocess

                uv_bin = shutil.which("uv")
                if uv_bin:
                    result = subprocess.run(
                        [
                            uv_bin,
                            "pip",
                            "install",
                            "--python",
                            sys.executable,
                            "modal",
                        ],
                        capture_output=True,
                        text=True,
                        errors='replace',
                    )
                else:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "modal"],
                        capture_output=True,
                        text=True,
                        errors='replace',
                    )
                if result.returncode == 0:
                    print_success("modal SDK установлен")
                else:
                    print_warning("Установка не удалась — запустите вручную: pip install modal")

            # Modal token
            print()
            print_info("Аутентификация Modal:")
            print_info("  Получите токен на: https://modal.com/settings")
            existing_token = get_env_value("MODAL_TOKEN_ID")
            if existing_token:
                print_info("  Токен Modal: уже настроен")
                if prompt_yes_no("  Обновить учётные данные Modal?", False):
                    token_id = prompt("    Token ID Modal", password=True)
                    token_secret = prompt("    Token Secret Modal", password=True)
                    if token_id:
                        save_env_value("MODAL_TOKEN_ID", token_id)
                    if token_secret:
                        save_env_value("MODAL_TOKEN_SECRET", token_secret)
            else:
                token_id = prompt("    Modal Token ID", password=True)
                token_secret = prompt("    Modal Token Secret", password=True)
                if token_id:
                    save_env_value("MODAL_TOKEN_ID", token_id)
                if token_secret:
                    save_env_value("MODAL_TOKEN_SECRET", token_secret)

        _prompt_container_resources(config)

    elif selected_backend == "daytona":
        print_success("Терминальный бэкенд: Daytona")
        print_info("Постоянные облачные среды разработки.")
        print_info("Каждая сессия получает выделенную песочницу с постоянством файловой системы.")
        print_info("Зарегистрируйтесь на: https://daytona.io")

        # Check if daytona SDK is installed
        try:
            __import__("daytona")
        except ImportError:
            print_info("Установка daytona SDK...")
            import subprocess

            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, "daytona"],
                    capture_output=True,
                    text=True,
                    errors='replace',
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "daytona"],
                    capture_output=True,
                    text=True,
                    errors='replace',
                )
            if result.returncode == 0:
                print_success("daytona SDK установлен")
            else:
                print_warning("Установка не удалась — запустите вручную: pip install daytona")
                if result.stderr:
                    print_info(f"  Error: {result.stderr.strip().splitlines()[-1]}")

        # Daytona API key
        print()
        existing_key = get_env_value("DAYTONA_API_KEY")
        if existing_key:
            print_info("  Daytona API key: already configured")
            if prompt_yes_no("  Update API key?", False):
                api_key = prompt("    Daytona API key", password=True)
                if api_key:
                    save_env_value("DAYTONA_API_KEY", api_key)
                    print_success("Обновлено")
        else:
            api_key = prompt("    Daytona API key", password=True)
            if api_key:
                save_env_value("DAYTONA_API_KEY", api_key)
                print_success("Настроено")

        # Daytona image
        current_image = cfg_get(config, "terminal", "daytona_image", default="nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  Sandbox image", current_image)
        config["terminal"]["daytona_image"] = image
        save_env_value("TERMINAL_DAYTONA_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "vercel_sandbox":
        print_success("Терминальный бэкенд: Vercel Sandbox")
        print_info("Облачные микроВМ песочницы с постоянством файловой системы на основе снимков.")
        print_info("Требуется опциональный SDK: pip install 'hermes-agent[vercel]'")

        try:
            __import__("vercel")
        except ImportError:
            print_info("Установка vercel SDK...")
            import subprocess

            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, "vercel"],
                    capture_output=True,
                    text=True,
                    errors='replace',
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "vercel"],
                    capture_output=True,
                    text=True,
                    errors='replace',
                )
            if result.returncode == 0:
                print_success("vercel SDK установлен")
            else:
                print_warning("Установка не удалась — запустите вручную: pip install 'hermes-agent[vercel]'")
                if result.stderr:
                    print_info(f"  Error: {result.stderr.strip().splitlines()[-1]}")

        _prompt_vercel_sandbox_settings(config)

    elif selected_backend == "ssh":
        print_success("Терминальный бэкенд: SSH")
        print_info("Выполнение команд на удалённой машине через SSH.")

        # SSH host
        current_host = get_env_value("TERMINAL_SSH_HOST") or ""
        host = prompt("  SSH host (hostname or IP)", current_host)
        if host:
            save_env_value("TERMINAL_SSH_HOST", host)

        # SSH user
        current_user = get_env_value("TERMINAL_SSH_USER") or ""
        user = prompt("  SSH user", current_user or os.getenv("USER", ""))
        if user:
            save_env_value("TERMINAL_SSH_USER", user)

        # SSH port
        current_port = get_env_value("TERMINAL_SSH_PORT") or "22"
        port = prompt("  SSH port", current_port)
        if port and port != "22":
            save_env_value("TERMINAL_SSH_PORT", port)

        # SSH key
        current_key = get_env_value("TERMINAL_SSH_KEY") or ""
        default_key = str(Path.home() / ".ssh" / "id_rsa")
        ssh_key = prompt("  SSH private key path", current_key or default_key)
        if ssh_key:
            save_env_value("TERMINAL_SSH_KEY", ssh_key)

        # Test connection
        if host and prompt_yes_no("  Test SSH connection?", True):
            print_info("  Тестирование соединения...")
            import subprocess

            ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            if port and port != "22":
                ssh_cmd.extend(["-p", port])
            ssh_cmd.append(f"{user}@{host}" if user else host)
            ssh_cmd.append("echo ok")
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10, errors='replace')
            if result.returncode == 0:
                print_success("SSH подключение успешно!")
            else:
                print_warning(f"  SSH соединение не удалось: {result.stderr.strip()}")
                print_info("  Проверьте ваш SSH ключ и настройки хоста.")

    # Sync terminal backend to .env so terminal_tool picks it up directly.
    # config.yaml is the source of truth, but terminal_tool reads TERMINAL_ENV.
    save_env_value("TERMINAL_ENV", selected_backend)
    if selected_backend == "modal":
        save_env_value("TERMINAL_MODAL_MODE", config["terminal"].get("modal_mode", "auto"))
    if selected_backend == "vercel_sandbox":
        save_env_value("TERMINAL_VERCEL_RUNTIME", config["terminal"].get("vercel_runtime", "node24"))
    save_config(config)
    print()
    print_success(f"Terminal backend set to: {selected_backend}")


# =============================================================================
# Section 3: Agent Settings
# =============================================================================


def _apply_default_agent_settings(config: dict):
    """Apply recommended defaults for all agent settings without prompting."""
    config.setdefault("agent", {})["max_turns"] = 90
    # config.yaml is the authoritative source for max_turns; the gateway
    # bridges it into HERMES_MAX_ITERATIONS at startup. We no longer write
    # to .env to avoid the dual-source inconsistency that caused the
    # 60-vs-500 bug (stale .env entry silently shadowing config.yaml).
    remove_env_value("HERMES_MAX_ITERATIONS")

    config.setdefault("display", {})["tool_progress"] = "all"

    config.setdefault("compression", {})["enabled"] = True
    config["compression"]["threshold"] = 0.50

    config.setdefault("session_reset", {}).update({
        "mode": "both",
        "idle_minutes": 1440,
        "at_hour": 4,
    })

    save_config(config)
    print_success("Применены рекомендованные значения по умолчанию:")
    print_info("  Максимум итераций: 90")
    print_info("  Прогресс инструментов: все")
    print_info("  Порог сжатия: 0.50")
    print_info("  Сброс сессии: бездействие (1440 мин) + ежедневный (4:00)")
    print_info("  Запустите `hermes setup agent` позже для настройки.")


def setup_agent_settings(config: dict):
    """Configure agent behavior: iterations, progress display, compression, session reset."""

    print_header("Настройки агента")
    print_info(f"   Guide: {_DOCS_BASE}/user-guide/configuration")
    print()

    # ── Max Iterations ──
    # config.yaml is authoritative; read from there. If a legacy .env
    # entry is still around (from pre-PR#18413 setups), prefer the
    # config value so we don't surface a stale number to the user.
    current_max = str(cfg_get(config, "agent", "max_turns", default=90))
    print_info("Максимум итераций вызова инструментов за разговор.")
    print_info("Больше = более сложные задачи, но стоит больше токенов.")
    print_info(
        f"Нажмите Enter чтобы оставить {current_max}. Используйте 90 для большинства задач или 150+ для открытого исследования."
    )

    max_iter_str = prompt("Максимум итераций", current_max)
    try:
        max_iter = int(max_iter_str)
        if max_iter > 0:
            # Write to config.yaml (authoritative) only. Also clean up any
            # stale .env entry from earlier setup runs — the gateway's
            # bridge in gateway/run.py now unconditionally derives
            # HERMES_MAX_ITERATIONS from agent.max_turns at startup.
            config.setdefault("agent", {})["max_turns"] = max_iter
            config.pop("max_turns", None)
            remove_env_value("HERMES_MAX_ITERATIONS")
            print_success(f"Максимум итераций установлен в {max_iter}")
    except ValueError:
        print_warning("Некорректное число, сохраняем текущее значение")

    # ── Tool Progress Display ──
    print_info("")
    print_info("Отображение прогресса инструментов")
    print_info("Управляет тем сколько активности инструментов показывается (CLI и messaging).")
    print_info("  off     — Тихо, только финальный ответ")
    print_info("  new     — Показывать имя инструмента только когда оно меняется (меньше шума)")
    print_info("  all     — Показывать каждый вызов инструмента с коротким предпросмотром")
    print_info("  verbose — Полные аргументы, результаты и отладочные логи")

    current_mode = cfg_get(config, "display", "tool_progress", default="all")
    mode = prompt("Режим прогресса инструментов", current_mode)
    if mode.lower() in {"off", "new", "all", "verbose"}:
        if "display" not in config:
            config["display"] = {}
        config["display"]["tool_progress"] = mode.lower()
        save_config(config)
        print_success(f"Прогресс инструментов установлен в: {mode.lower()}")
    else:
        print_warning(f"Неизвестный режим '{mode}', сохраняем '{current_mode}'")

    # ── Context Compression ──
    print_header("Сжатие контекста")
    print_info("Автоматически суммирует старые сообщения когда контекст становится слишком длинным.")
    print_info("Более высокий порог = сжимать позже (использовать больше контекста). Ниже = сжимать раньше.")

    config.setdefault("compression", {})["enabled"] = True

    current_threshold = cfg_get(config, "compression", "threshold", default=0.50)
    threshold_str = prompt("Compression threshold (0.5-0.95)", str(current_threshold))
    try:
        threshold = float(threshold_str)
        if 0.5 <= threshold <= 0.95:
            config["compression"]["threshold"] = threshold
    except ValueError:
        pass

    print_success(
        f"Context compression threshold set to {config['compression'].get('threshold', 0.50)}"
    )

    # ── Session Reset Policy ──
    print_header("Политика сброса сессии")
    print_info(
        "Сессии сообщений (Telegram, Discord и т.д.) накапливают контекст со временем."
    )
    print_info(
        "Каждое сообщение добавляется в историю разговора, что означает растущие затраты API."
    )
    print_info("")
    print_info(
        "Чтобы управлять этим, сессии могут автоматически сбрасываться после периода бездействия"
    )
    print_info(
        "или в фиксированное время каждый день. Когда это происходит, агент сохраняет важное"
    )
    print_info(
        "в свою постоянную память сначала — но контекст разговора очищается."
    )
    print_info("")
    print_info("Вы также можете вручную сбросить в любое время введя /reset в чате.")
    print_info("")

    reset_choices = [
        "Бездействие + ежедневный сброс (рекомендуется — сбрасывается то что наступит раньше)",
        "Только бездействие (сброс после N минут без сообщений)",
        "Только ежедневный (сброс в фиксированный час каждый день)",
        "Никогда не сбрасывать автоматически (контекст живёт до /reset или сжатия контекста)",
        "Сохранить текущие настройки",
    ]

    current_policy = config.get("session_reset", {})
    current_mode = current_policy.get("mode", "both")
    current_idle = current_policy.get("idle_minutes", 1440)
    current_hour = current_policy.get("at_hour", 4)

    default_reset = {"both": 0, "idle": 1, "daily": 2, "none": 3}.get(current_mode, 0)

    reset_idx = prompt_choice("Режим сброса сессии:", reset_choices, default_reset)

    config.setdefault("session_reset", {})

    if reset_idx == 0:  # Both
        config["session_reset"]["mode"] = "both"
        idle_str = prompt("  Inactivity timeout (minutes)", str(current_idle))
        try:
            idle_val = int(idle_str)
            if idle_val > 0:
                config["session_reset"]["idle_minutes"] = idle_val
        except ValueError:
            pass
        hour_str = prompt("  Daily reset hour (0-23, local time)", str(current_hour))
        try:
            hour_val = int(hour_str)
            if 0 <= hour_val <= 23:
                config["session_reset"]["at_hour"] = hour_val
        except ValueError:
            pass
        print_success(
            f"Sessions reset after {config['session_reset'].get('idle_minutes', 1440)} min idle or daily at {config['session_reset'].get('at_hour', 4)}:00"
        )
    elif reset_idx == 1:  # Idle only
        config["session_reset"]["mode"] = "idle"
        idle_str = prompt("  Inactivity timeout (minutes)", str(current_idle))
        try:
            idle_val = int(idle_str)
            if idle_val > 0:
                config["session_reset"]["idle_minutes"] = idle_val
        except ValueError:
            pass
        print_success(
            f"Sessions reset after {config['session_reset'].get('idle_minutes', 1440)} min of inactivity"
        )
    elif reset_idx == 2:  # Daily only
        config["session_reset"]["mode"] = "daily"
        hour_str = prompt("  Daily reset hour (0-23, local time)", str(current_hour))
        try:
            hour_val = int(hour_str)
            if 0 <= hour_val <= 23:
                config["session_reset"]["at_hour"] = hour_val
        except ValueError:
            pass
        print_success(
            f"Sessions reset daily at {config['session_reset'].get('at_hour', 4)}:00"
        )
    elif reset_idx == 3:  # None
        config["session_reset"]["mode"] = "none"
        print_info(
            "Sessions will never auto-reset. Context is managed only by compression."
        )
        print_warning(
            "Long conversations will grow in cost. Use /reset manually when needed."
        )
    # else: keep current (idx == 4)

    save_config(config)


# =============================================================================
# Section 4: Messaging Platforms (Gateway)
# =============================================================================


def _setup_telegram():
    """Configure Telegram bot credentials and allowlist."""
    print_header("Telegram")
    existing = get_env_value("TELEGRAM_BOT_TOKEN")
    if existing:
        print_info("Telegram: уже настроен")
        if not prompt_yes_no("Перенастроить Telegram?", False):
            # Check missing allowlist on existing config
            if not get_env_value("TELEGRAM_ALLOWED_USERS"):
                print_info("⚠️  В Telegram нет списка разрешений — любой может использовать вашего бота!")
                if prompt_yes_no("Add allowed users now?", True):
                    print_info("   Чтобы найти ваш Telegram user ID: напишите @userinfobot")
                    allowed_users = prompt("Allowed user IDs (comma-separated)")
                    if allowed_users:
                        save_env_value("TELEGRAM_ALLOWED_USERS", allowed_users.replace(" ", ""))
                        print_success("Список разрешений Telegram настроен")
            return

    print_info("Создайте бота через @BotFather в Telegram")
    import re

    while True:
        token = prompt("Telegram bot token", password=True)
        if not token:
            return
        if not re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", token):
            print_error(
                "Invalid token format. Expected: <numeric_id>:<alphanumeric_hash> "
                "(e.g., 123456789:ABCdefGHI-jklMNOpqrSTUvwxYZ)"
            )
            continue
        break
    save_env_value("TELEGRAM_BOT_TOKEN", token)
    print_success("Токен Telegram сохранён")

    print()
    print_info("🔒 Безопасность: Ограничьте кто может использовать вашего бота")
    print_info("   Чтобы найти ваш Telegram user ID:")
    print_info("   1. Напишите @userinfobot в Telegram")
    print_info("   2. Он ответит вашим числовым ID (например, 123456789)")
    print()
    allowed_users = prompt(
        "Разрешённые user ID (через запятую, оставьте пустым для открытого доступа)"
    )
    if allowed_users:
        save_env_value("TELEGRAM_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Список разрешений Telegram настроен — только указанные пользователи могут использовать бота")
    else:
        print_info("⚠️  Список разрешений не установлен — любой кто найдёт вашего бота может использовать его!")

    print()
    print_info("📬 Домашний канал: куда Hermes доставляет результаты cron задач,")
    print_info("   кросс-платформенные сообщения и уведомления.")
    print_info("   Для Telegram DM это ваш user ID (как выше).")

    first_user_id = allowed_users.split(",")[0].strip() if allowed_users else ""
    if first_user_id:
        if prompt_yes_no(f"Использовать ваш user ID ({first_user_id}) в качестве домашнего канала?", True):
            save_env_value("TELEGRAM_HOME_CHANNEL", first_user_id)
            print_success(f"Telegram home channel set to {first_user_id}")
        else:
            home_channel = prompt("ID домашнего канала (или оставьте пустым чтобы настроить позже через /set-home в Telegram)")
            if home_channel:
                save_env_value("TELEGRAM_HOME_CHANNEL", home_channel)
    else:
        print_info("   Вы также можете настроить это позже введя /set-home в вашем Telegram чате.")
        home_channel = prompt("ID домашнего канала (оставьте пустым чтобы настроить позже)")
        if home_channel:
            save_env_value("TELEGRAM_HOME_CHANNEL", home_channel)


def _setup_discord():
    """Configure Discord bot credentials and allowlist."""
    print_header("Discord")
    existing = get_env_value("DISCORD_BOT_TOKEN")
    if existing:
        print_info("Discord: уже настроен")
        if not prompt_yes_no("Reconfigure Discord?", False):
            if not get_env_value("DISCORD_ALLOWED_USERS"):
                print_info("⚠️  В Discord нет списка разрешений — любой может использовать вашего бота!")
                if prompt_yes_no("Add allowed users now?", True):
                    print_info("   Чтобы найти Discord ID: Включите Developer Mode, ПКМ по имени → Copy ID")
                    allowed_users = prompt("Allowed user IDs (comma-separated)")
                    if allowed_users:
                        cleaned_ids = _clean_discord_user_ids(allowed_users)
                        save_env_value("DISCORD_ALLOWED_USERS", ",".join(cleaned_ids))
                        print_success("Список разрешений Discord настроен")
            return

    print_info("Создайте бота на https://discord.com/developers/applications")
    token = prompt("Discord bot token", password=True)
    if not token:
        return
    save_env_value("DISCORD_BOT_TOKEN", token)
    print_success("Токен Discord сохранён")

    print()
    print_info("🔒 Безопасность: Ограничьте кто может использовать вашего бота")
    print_info("   Чтобы найти ваш Discord user ID:")
    print_info("   1. Включите Developer Mode в настройках Discord")
    print_info("   2. ПКМ по вашему имени → Copy ID")
    print()
    print_info("   Вы также можете использовать Discord usernames (разрешается при запуске шлюза).")
    print()
    allowed_users = prompt(
        "Разрешённые ID или имена пользователей (через запятую, оставьте пустым для открытого доступа)"
    )
    if allowed_users:
        cleaned_ids = _clean_discord_user_ids(allowed_users)
        save_env_value("DISCORD_ALLOWED_USERS", ",".join(cleaned_ids))
        print_success("Список разрешений Discord настроен")
    else:
        print_info("⚠️  Список разрешений не установлен — любой в серверах с вашим ботом может использовать его!")

    print()
    print_info("📬 Домашний канал: куда Hermes доставляет результаты cron задач,")
    print_info("   кросс-платформенные сообщения и уведомления.")
    print_info("   Чтобы найти ID канала: ПКМ по каналу → Copy Channel ID")
    print_info("   (требуется Developer Mode в настройках Discord)")
    print_info("   Вы также можете настроить это позже введя /set-home в канале Discord.")
    home_channel = prompt("ID домашнего канала (оставьте пустым чтобы настроить позже через /set-home)")
    if home_channel:
        save_env_value("DISCORD_HOME_CHANNEL", home_channel)


def _clean_discord_user_ids(raw: str) -> list:
    """Strip common Discord mention prefixes from a comma-separated ID string."""
    cleaned = []
    for uid in raw.replace(" ", "").split(","):
        uid = uid.strip()
        if uid.startswith("<@") and uid.endswith(">"):
            uid = uid.lstrip("<@!").rstrip(">")
        if uid.lower().startswith("user:"):
            uid = uid[5:]
        if uid:
            cleaned.append(uid)
    return cleaned


def _setup_slack():
    """Configure Slack bot credentials."""
    print_header("Slack")
    existing = get_env_value("SLACK_BOT_TOKEN")
    if existing:
        print_info("Slack: уже настроен")
        if not prompt_yes_no("Reconfigure Slack?", False):
            # Even without reconfiguring, offer to refresh the manifest so
            # new commands (e.g. /btw, /stop, ...) get registered in Slack.
            if prompt_yes_no(
                "Сгенерировать заново manifest приложения Slack с последним списком команд? "
                "(рекомендуется после `hermes update`)",
                True,
            ):
                _write_slack_manifest_and_instruct()
            return

    print_info("Шаги по созданию Slack приложения:")
    print_info("   1. Перейдите на https://api.slack.com/apps → Create New App")
    print_info("      Выберите 'From an app manifest' — мы сгенерируем его для вас ниже.")
    print_info("   2. Включите Socket Mode: Settings → Socket Mode → Enable")
    print_info("      • Создайте App-Level Token с scope 'connections:write'")
    print_info("   3. Установите в Workspace: Settings → Install App")
    print_info("   4. После установки, пригласите бота в каналы: /invite @YourBot")
    print()
    print_info("   Полное руководство: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack/")
    print()

    # Сгенерировать и записать manifest заранее чтобы пользователь мог вставить его в
    # поток "Create from manifest" вместо кликанья через scopes /
    # events / slash commands по одному.
    _write_slack_manifest_and_instruct()

    print()
    bot_token = prompt("Slack Bot Token (xoxb-...)", password=True)
    if not bot_token:
        return
    save_env_value("SLACK_BOT_TOKEN", bot_token)
    app_token = prompt("Slack App Token (xapp-...)", password=True)
    if app_token:
        save_env_value("SLACK_APP_TOKEN", app_token)
    print_success("Токены Slack сохранены")

    print()
    print_info("🔒 Безопасность: Ограничьте кто может использовать вашего бота")
    print_info("   Чтобы найти Member ID: кликните по имени пользователя → View full profile → ⋮ → Copy member ID")
    print()
    allowed_users = prompt(
        "Разрешённые user ID (через запятую, оставьте пустым чтобы отказать всем кроме спаренных пользователей)"
    )
    if allowed_users:
        save_env_value("SLACK_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Список разрешений Slack настроен")
    else:
        print_warning("⚠️  Список разрешений Slack не установлен — несопаренные пользователи будут отклонены по умолчанию.")
        print_info("   Установите SLACK_ALLOW_ALL_USERS=true или GATEWAY_ALLOW_ALL_USERS=true только если вы намеренно хотите открыть доступ workspace.")

    print()
    print_info("📬 Домашний канал: куда Hermes доставляет результаты cron задач,")
    print_info("   кросс-платформенные сообщения и уведомления.")
    print_info("   Чтобы найти ID канала: откройте канал в Slack, затем ПКМ")
    print_info("   по имени канала → Copy link — ID начинается с C (например, C01ABC2DE3F).")
    print_info("   Вы также можете настроить это позже введя /set-home в канале Slack.")
    home_channel = prompt("ID домашнего канала (оставьте пустым чтобы настроить позже через /set-home)")
    if home_channel:
        save_env_value("SLACK_HOME_CHANNEL", home_channel.strip())


def _write_slack_manifest_and_instruct():
    """Generate the Slack manifest, write it under HERMES_HOME, and print
    paste-into-Slack instructions.

    Exposed as its own helper so both the initial setup flow and the
    "reconfigure? → no" branch can refresh the manifest without the user
    re-entering tokens. Failures are non-fatal — if the manifest write
    fails for any reason, we print a warning and skip rather than abort
    the whole Slack setup.
    """
    try:
        from hermes_cli.slack_cli import _build_full_manifest
        from hermes_constants import get_hermes_home

        manifest = _build_full_manifest(
            bot_name="Hermes",
            bot_description="Your Hermes agent on Slack",
        )
        target = Path(get_hermes_home()) / "slack-manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        target.write_text(
            _json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print_success(f"Slack app manifest записан в: {target}")
        print_info(
            "   Вставьте его на https://api.slack.com/apps → ваше приложение → Features "
            "→ App Manifest → Edit, затем Save.  Slack попросит "
            "переустановить если scopes или slash commands изменились."
        )
        print_info(
            "   Запустите `hermes slack manifest --write` в любое время для обновления после "
            "того как Hermes добавит новые команды."
        )
    except Exception as exc:  # pragma: no cover - best-effort UX helper
        print_warning(f"Не удалось записать Slack manifest: {exc}")
        print_info(
            "   Вы можете сгенерировать его вручную позже с помощью: "
            "hermes slack manifest --write"
        )


def _setup_matrix():
    """Configure Matrix credentials."""
    print_header("Matrix")
    existing = get_env_value("MATRIX_ACCESS_TOKEN") or get_env_value("MATRIX_PASSWORD")
    if existing:
        print_info("Matrix: уже настроен")
        if not prompt_yes_no("Reconfigure Matrix?", False):
            return

    print_info("Работает с любым Matrix homeserver (Synapse, Conduit, Dendrite, или matrix.org).")
    print_info("   1. Создайте бота на вашем homeserver, или используйте свой аккаунт")
    print_info("   2. Получите access token из Element, или укажите user ID + password")
    print()
    homeserver = prompt("URL homeserver (например, https://matrix.example.org)")
    if homeserver:
        save_env_value("MATRIX_HOMESERVER", homeserver.rstrip("/"))

    print()
    print_info("Аутентификация: укажите access token (рекомендуется), или user ID + password.")
    token = prompt("Access token (оставьте пустым для входа по паролю)", password=True)
    if token:
        save_env_value("MATRIX_ACCESS_TOKEN", token)
        user_id = prompt("User ID (@bot:server — опционально, будет определён автоматически)")
        if user_id:
            save_env_value("MATRIX_USER_ID", user_id)
        print_success("Токен доступа Matrix сохранён")
    else:
        user_id = prompt("User ID (@bot:server)")
        if user_id:
            save_env_value("MATRIX_USER_ID", user_id)
        password = prompt("Password", password=True)
        if password:
            save_env_value("MATRIX_PASSWORD", password)
            print_success("Учётные данные Matrix сохранены")

    if token or get_env_value("MATRIX_PASSWORD"):
        print()
        want_e2ee = prompt_yes_no("Enable end-to-end encryption (E2EE)?", False)
        if want_e2ee:
            save_env_value("MATRIX_ENCRYPTION", "true")
            print_success("E2EE включено")

        matrix_pkg = "mautrix[encryption]" if want_e2ee else "mautrix"
        try:
            __import__("mautrix")
        except ImportError:
            print_info(f"Установка {matrix_pkg}...")
            import subprocess
            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, matrix_pkg],
                    capture_output=True, text=True, errors='replace',
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", matrix_pkg],
                    capture_output=True, text=True, errors='replace',
                )
            if result.returncode == 0:
                print_success(f"{matrix_pkg} установлен")
            else:
                print_warning(f"Установка не удалась — запустите вручную: pip install '{matrix_pkg}'")
                if result.stderr:
                    print_info(f"  Error: {result.stderr.strip().splitlines()[-1]}")

        print()
        print_info("🔒 Безопасность: Ограничьте кто может использовать вашего бота")
        print_info("   Matrix user IDs выглядят как @username:server")
        print()
        allowed_users = prompt("Разрешённые user ID (через запятую, оставьте пустым для открытого доступа)")
        if allowed_users:
            save_env_value("MATRIX_ALLOWED_USERS", allowed_users.replace(" ", ""))
            print_success("Список разрешений Matrix настроен")
        else:
            print_info("⚠️  Список разрешений не установлен — любой кто может написать боту может использовать его!")

        print()
        print_info("📬 Домашняя комната: куда Hermes доставляет результаты cron задач и уведомления.")
        print_info("   ID комнат выглядят как !abc123:server (показано в настройках комнаты Element)")
        print_info("   Вы также можете настроить это позже введя /set-home в комнате Matrix.")
        home_room = prompt("ID домашней комнаты (оставьте пустым чтобы настроить позже через /set-home)")
        if home_room:
            save_env_value("MATRIX_HOME_ROOM", home_room)


def _setup_mattermost():
    """Configure Mattermost bot credentials."""
    print_header("Mattermost")
    existing = get_env_value("MATTERMOST_TOKEN")
    if existing:
        print_info("Mattermost: уже настроен")
        if not prompt_yes_no("Перенастроить Mattermost?", False):
            return

    print_info("Работает с любым self-hosted Mattermost сервером.")
    print_info("   1. В Mattermost: Integrations → Bot Accounts → Add Bot Account")
    print_info("   2. Скопируйте токен бота")
    print()
    mm_url = prompt("URL сервера Mattermost (например, https://mm.example.com)")
    if mm_url:
        save_env_value("MATTERMOST_URL", mm_url.rstrip("/"))
    token = prompt("Токен бота", password=True)
    if not token:
        return
    save_env_value("MATTERMOST_TOKEN", token)
    print_success("Токен Mattermost сохранён")

    print()
    print_info("🔒 Безопасность: Ограничьте кто может использовать вашего бота")
    print_info("   Чтобы найти ваш user ID: кликните на аватар → Profile")
    print_info("   или используйте API: GET /api/v4/users/me")
    print()
    allowed_users = prompt("Разрешённые user ID (через запятую, оставьте пустым для открытого доступа)")
    if allowed_users:
        save_env_value("MATTERMOST_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Список разрешений Mattermost настроен")
    else:
        print_info("⚠️  Список разрешений не установлен — любой кто может написать боту может использовать его!")

    print()
    print_info("📬 Домашний канал: куда Hermes доставляет результаты cron задач и уведомления.")
    print_info("   Чтобы найти ID канала: кликните по имени канала → View Info → скопируйте ID")
    print_info("   Вы также можете настроить это позже введя /set-home в канале Mattermost.")
    home_channel = prompt("ID домашнего канала (оставьте пустым чтобы настроить позже через /set-home)")
    if home_channel:
        save_env_value("MATTERMOST_HOME_CHANNEL", home_channel)
    print_info("   Откройте конфиг в редакторе:  hermes config edit")


def _setup_bluebubbles():
    """Configure BlueBubbles iMessage gateway."""
    print_header("BlueBubbles (iMessage)")
    existing = get_env_value("BLUEBUBBLES_SERVER_URL")
    if existing:
        print_info("BlueBubbles: уже настроен")
        if not prompt_yes_no("Перенастроить BlueBubbles?", False):
            return

    print_info("Подключает Hermes к iMessage через BlueBubbles — бесплатный open-source")
    print_info("macOS сервер который соединяет iMessage с любым устройством.")
    print_info("   Требуется Mac с BlueBubbles Server v1.0.0+")
    print_info("   Скачать: https://bluebubbles.app/")
    print()
    print_info("В BlueBubbles Server → Settings → API, узнайте ваш Server URL и Password.")
    print()

    server_url = prompt("URL сервера BlueBubbles (например, http://192.168.1.10:1234)")
    if not server_url:
        print_warning("URL сервера требуется — пропускаем настройку BlueBubbles")
        return
    save_env_value("BLUEBUBBLES_SERVER_URL", server_url.rstrip("/"))

    password = prompt("Пароль сервера BlueBubbles", password=True)
    if not password:
        print_warning("Пароль требуется — пропускаем настройку BlueBubbles")
        return
    save_env_value("BLUEBUBBLES_PASSWORD", password)
    print_success("Учётные данные BlueBubbles сохранены")

    print()
    print_info("🔒 Безопасность: Ограничьте кто может писать вашему боту")
    print_info("   Используйте адреса iMessage: email (user@icloud.com) или телефон (+15551234567)")
    print()
    allowed_users = prompt("Разрешённые адреса iMessage (через запятую, оставьте пустым для открытого доступа)")
    if allowed_users:
        save_env_value("BLUEBUBBLES_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Список разрешений BlueBubbles настроен")
    else:
        print_info("⚠️  Список разрешений не установлен — любой кто может написать вам в iMessage может использовать бота!")

    print()
    print_info("📬 Домашний канал: телефон или email для доставки cron задач и уведомлений.")
    print_info("   Вы также можете настроить это позже с помощью /set-home в вашем iMessage чате.")
    home_channel = prompt("Адрес домашнего канала (оставьте пустым чтобы настроить позже)")
    if home_channel:
        save_env_value("BLUEBUBBLES_HOME_CHANNEL", home_channel)

    print()
    print_info("Расширенные настройки (значения по умолчанию подходят для большинства):")
    if prompt_yes_no("Настроить параметры прослушивателя вебхуков?", False):
        webhook_port = prompt("Порт прослушивателя вебхуков (по умолчанию: 8645)")
        if webhook_port:
            try:
                save_env_value("BLUEBUBBLES_WEBHOOK_PORT", str(int(webhook_port)))
                print_success(f"Порт вебхука установлен в {webhook_port}")
            except ValueError:
                print_warning("Некорректный номер порта, используем по умолчанию 8645")

    print()
    print_info("Требуется BlueBubbles Private API helper для индикации набора,")
    print_info("прочитанных уведомлений и реакций tapback. Базовые сообщения работают без него.")
    print_info("   Установка: https://docs.bluebubbles.app/helper-bundle/installation")


def _setup_qqbot():
    """Настроить QQ Bot (Official API v2) через настройку шлюза."""
    from hermes_cli.gateway import _setup_qqbot as _gateway_setup_qqbot
    _gateway_setup_qqbot()


def _setup_webhooks():
    """Настроить интеграцию вебхуков."""
    print_header("Webhooks")
    existing = get_env_value("WEBHOOK_ENABLED")
    if existing:
        print_info("Webhooks: уже настроены")
        if not prompt_yes_no("Перенастроить вебхуки?", False):
            return

    print()
    print_warning("⚠  Webhook и SMS платформы требуют открытия портов шлюза в интернет.")
    print_warning("   Для безопасности, запускайте шлюз в изолированной среде")
    print_warning("   (Docker, VM, и т.д.) чтобы ограничить последствия от prompt injection.")
    print()
    print_info("   Полное руководство: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/")
    print()

    port = prompt("Порт вебхука (по умолчанию 8644)")
    if port:
        try:
            save_env_value("WEBHOOK_PORT", str(int(port)))
            print_success(f"Порт вебхука установлен в {port}")
        except ValueError:
            print_warning("Некорректный номер порта, используем по умолчанию 8644")

    secret = prompt("Глобальный HMAC secret (общий для всех маршрутов)", password=True)
    if secret:
        save_env_value("WEBHOOK_SECRET", secret)
        print_success("Webhook secret сохранён")
    else:
        print_warning("Secret не установлен — вы должны настроить per-route secrets в config.yaml")

    save_env_value("WEBHOOK_ENABLED", "true")
    print()
    print_success("Вебхуки включены! Следующие шаги:")
    from hermes_constants import display_hermes_home as _dhh
    print_info(f"   1. Определите маршруты вебхуков в {_dhh()}/config.yaml")
    print_info("   2. Направьте ваш сервис (GitHub, GitLab, и т.д.) на:")
    print_info("      http://your-server:8644/webhooks/<route-name>")
    print()
    print_info("   Руководство по настройке маршрутов:")
    print_info("   https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/#configuring-routes")
    print()
    print_info("   Откройте конфиг в редакторе:  hermes config edit")
    print_info("   Откройте конфиг в редакторе:  hermes config edit")


def setup_gateway(config: dict):
    """Configure messaging platform integrations."""
    from hermes_cli.gateway import _all_platforms, _platform_status, _configure_platform

    print_header("Платформы сообщений")
    print_info("Подключитесь к платформам сообщений чтобы общаться с Hermes из любой точки.")
    print_info("Переключите пробелом, подтвердите Enter.")
    print()

    platforms = _all_platforms()

    # Build checklist, pre-selecting already-configured platforms.
    items = []
    pre_selected = []
    for i, plat in enumerate(platforms):
        status = _platform_status(plat)
        items.append(f"{plat['emoji']} {plat['label']}  ({status})")
        if status == "configured":
            pre_selected.append(i)

    selected = prompt_checklist("Select platforms to configure:", items, pre_selected)

    if not selected:
        print_info("Платформы не выбраны. Запустите 'hermes setup gateway' позже для настройки.")
        return

    for idx in selected:
        _configure_platform(platforms[idx])

    # ── Gateway Service Setup ──
    # Count any platform (built-in or plugin) the user configured during this
    # setup pass — reuses ``_platform_status`` so plugin platforms like IRC
    # are picked up without another hard-coded env-var list.
    def _is_progress(status: str) -> bool:
        s = status.lower()
        return not (
            s == "not configured"
            or s.startswith("partially")
            or s.startswith("plugin disabled")
        )

    any_messaging = any(
        _is_progress(_platform_status(p)) for p in _all_platforms()
    )
    if any_messaging:
        print()
        print_info("━" * 50)
        print_success("Messaging platforms configured!")

        # Check if any home channels are missing
        missing_home = []
        if get_env_value("TELEGRAM_BOT_TOKEN") and not get_env_value(
            "TELEGRAM_HOME_CHANNEL"
        ):
            missing_home.append("Telegram")
        if get_env_value("DISCORD_BOT_TOKEN") and not get_env_value(
            "DISCORD_HOME_CHANNEL"
        ):
            missing_home.append("Discord")
        if get_env_value("SLACK_BOT_TOKEN") and not get_env_value("SLACK_HOME_CHANNEL"):
            missing_home.append("Slack")
        if get_env_value("BLUEBUBBLES_SERVER_URL") and not get_env_value("BLUEBUBBLES_HOME_CHANNEL"):
            missing_home.append("BlueBubbles")
        if get_env_value("QQ_APP_ID") and not (
            get_env_value("QQBOT_HOME_CHANNEL") or get_env_value("QQ_HOME_CHANNEL")
        ):
            missing_home.append("QQBot")

        if missing_home:
            print()
            print_warning(f"No home channel set for: {', '.join(missing_home)}")
            print_info("   Without a home channel, cron jobs and cross-platform")
            print_info("   messages can't be delivered to those platforms.")
            print_info("   Set one later with /set-home in your chat, or:")
            for plat in missing_home:
                print_info(
                    f"     hermes config set {plat.upper()}_HOME_CHANNEL <channel_id>"
                )

        # Offer to install the gateway as a system service
        import platform as _platform

        _is_linux = _platform.system() == "Linux"
        _is_macos = _platform.system() == "Darwin"
        _is_windows = _platform.system() == "Windows"

        from hermes_cli.gateway import (
            _is_service_installed,
            _is_service_running,
            supports_systemd_services,
            has_conflicting_systemd_units,
            has_legacy_hermes_units,
            install_linux_gateway_from_setup,
            print_systemd_scope_conflict_warning,
            print_legacy_unit_warning,
            systemd_start,
            systemd_restart,
            launchd_install,
            launchd_start,
            launchd_restart,
            UserSystemdUnavailableError,
            SystemScopeRequiresRootError,
            _system_scope_wizard_would_need_root,
            _print_system_scope_remediation,
        )

        service_installed = _is_service_installed()
        service_running = _is_service_running()
        supports_systemd = supports_systemd_services()
        supports_service_manager = supports_systemd or _is_macos or _is_windows

        print()
        if supports_systemd and has_conflicting_systemd_units():
            print_systemd_scope_conflict_warning()
            print()

        if supports_systemd and has_legacy_hermes_units():
            print_legacy_unit_warning()
            print()

        if service_running:
            if supports_systemd and _system_scope_wizard_would_need_root():
                _print_system_scope_remediation("restart")
            elif prompt_yes_no("  Restart the gateway to pick up changes?", True):
                try:
                    if supports_systemd:
                        systemd_restart()
                    elif _is_macos:
                        launchd_restart()
                    elif _is_windows:
                        from hermes_cli import gateway_windows
                        gateway_windows.restart()
                except UserSystemdUnavailableError as e:
                    print_error("  Restart failed — user systemd not reachable:")
                    for line in str(e).splitlines():
                        print(f"  {line}")
                except SystemScopeRequiresRootError as e:
                    # Defense in depth: the pre-check above should have
                    # caught this, but a race (unit file appearing mid-run)
                    # could still land here. Previously this exited the
                    # whole wizard via sys.exit(1).
                    print_error(f"  Restart failed: {e}")
                    _print_system_scope_remediation("restart")
                except Exception as e:
                    print_error(f"  Restart failed: {e}")
        elif service_installed:
            if supports_systemd and _system_scope_wizard_would_need_root():
                _print_system_scope_remediation("start")
            elif prompt_yes_no("  Start the gateway service?", True):
                try:
                    if supports_systemd:
                        systemd_start()
                    elif _is_macos:
                        launchd_start()
                    elif _is_windows:
                        from hermes_cli import gateway_windows
                        gateway_windows.start()
                except UserSystemdUnavailableError as e:
                    print_error("  Start failed — user systemd not reachable:")
                    for line in str(e).splitlines():
                        print(f"  {line}")
                except SystemScopeRequiresRootError as e:
                    print_error(f"  Start failed: {e}")
                    _print_system_scope_remediation("start")
                except Exception as e:
                    print_error(f"  Start failed: {e}")
        elif supports_service_manager:
            if supports_systemd:
                svc_name = "systemd"
            elif _is_macos:
                svc_name = "launchd"
            else:
                svc_name = "Scheduled Task"
            if prompt_yes_no(
                f"  Install the gateway as a {svc_name} service? (runs in background, starts on boot)",
                True,
            ):
                try:
                    installed_scope = None
                    did_install = False
                    started_inline = False
                    if supports_systemd:
                        installed_scope, did_install = install_linux_gateway_from_setup(force=False)
                    elif _is_macos:
                        launchd_install(force=False)
                        did_install = True
                    else:
                        # gateway_windows.install() registers the Scheduled
                        # Task AND starts it immediately (via schtasks /Run
                        # or a direct spawn fallback), so no separate start
                        # prompt is needed here.
                        from hermes_cli import gateway_windows
                        gateway_windows.install(force=False)
                        did_install = True
                        started_inline = True
                    print()
                    if did_install and not started_inline and prompt_yes_no("  Start the service now?", True):
                        try:
                            if supports_systemd:
                                systemd_start(system=installed_scope == "system")
                            elif _is_macos:
                                launchd_start()
                        except UserSystemdUnavailableError as e:
                            print_error("  Start failed — user systemd not reachable:")
                            for line in str(e).splitlines():
                                print(f"  {line}")
                        except SystemScopeRequiresRootError as e:
                            print_error(f"  Start failed: {e}")
                            _print_system_scope_remediation("start")
                        except Exception as e:
                            print_error(f"  Start failed: {e}")
                except Exception as e:
                    print_error(f"  Install failed: {e}")
                    print_info("  You can try manually: hermes gateway install")
            else:
                print_info("  You can install later: hermes gateway install")
                if supports_systemd:
                    print_info("  Or as a boot-time service: sudo hermes gateway install --system")
                print_info("  Or run in foreground:  hermes gateway")
        else:
            from hermes_constants import is_container
            if is_container():
                print_info("Start the gateway to bring your bots online:")
                print_info("   hermes gateway run          # Run as container main process")
                print_info("")
                print_info("For automatic restarts, use a Docker restart policy:")
                print_info("   docker run --restart unless-stopped ...")
                print_info("   docker restart <container>  # Manual restart")
            else:
                print_info("Start the gateway to bring your bots online:")
                print_info("   hermes gateway              # Run in foreground")

        print_info("━" * 50)


# =============================================================================
# Section 5: Tool Configuration (delegates to unified tools_config.py)
# =============================================================================


def setup_tools(config: dict, first_install: bool = False):
    """Configure tools — delegates to the unified tools_command() in tools_config.py.

    Both `hermes setup tools` and `hermes tools` use the same flow:
    platform selection → toolset toggles → provider/API key configuration.

    Args:
        first_install: When True, uses the simplified first-install flow
            (no platform menu, prompts for all unconfigured API keys).
    """
    from hermes_cli.tools_config import tools_command

    tools_command(first_install=first_install, config=config)


# =============================================================================
# Post-Migration Section Skip Logic
# =============================================================================


def _model_section_has_credentials(config: dict) -> bool:
    """Return True when any known inference provider has usable credentials.

    Sources of truth:
      * ``PROVIDER_REGISTRY`` in ``hermes_cli.auth`` — lists every supported
        provider along with its ``api_key_env_vars``.
      * ``active_provider`` in the auth store — covers OAuth device-code /
        external-OAuth providers (Nous, Codex, Qwen, Gemini CLI, ...).
      * The legacy OpenRouter aggregator env vars, which route generic
        ``OPENAI_API_KEY`` / ``OPENROUTER_API_KEY`` values through OpenRouter.
    """
    try:
        from hermes_cli.auth import get_active_provider
        if get_active_provider():
            return True
    except Exception:
        pass

    try:
        from hermes_cli.auth import PROVIDER_REGISTRY
    except Exception:
        PROVIDER_REGISTRY = {}  # type: ignore[assignment]

    def _has_key(pconfig) -> bool:
        for env_var in pconfig.api_key_env_vars:
            # CLAUDE_CODE_OAUTH_TOKEN is set by Claude Code itself, not by
            # the user — mirrors is_provider_explicitly_configured in auth.py.
            if env_var == "CLAUDE_CODE_OAUTH_TOKEN":
                continue
            if get_env_value(env_var):
                return True
        return False

    # Prefer the provider declared in config.yaml, avoids false positives
    # from stray env vars (GH_TOKEN, etc.) when the user has already picked
    # a different provider.
    model_cfg = config.get("model") if isinstance(config, dict) else None
    if isinstance(model_cfg, dict):
        provider_id = (model_cfg.get("provider") or "").strip().lower()
        if provider_id in PROVIDER_REGISTRY:
            if _has_key(PROVIDER_REGISTRY[provider_id]):
                return True
        if provider_id == "openrouter":
            for env_var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
                if get_env_value(env_var):
                    return True

    # OpenRouter aggregator fallback (no provider declared in config).
    for env_var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if get_env_value(env_var):
            return True

    for pid, pconfig in PROVIDER_REGISTRY.items():
        # Skip copilot in auto-detect: GH_TOKEN / GITHUB_TOKEN are
        # commonly set for git tooling.  Mirrors resolve_provider in auth.py.
        if pid == "copilot":
            continue
        if _has_key(pconfig):
            return True
    return False


def _gateway_platform_short_label(label: str) -> str:
    """Strip trailing parenthetical qualifiers from a gateway platform label."""
    base = label.split("(", 1)[0].strip()
    return base or label


def _get_section_config_summary(config: dict, section_key: str) -> Optional[str]:
    """Return a short summary if a setup section is already configured, else None.

    Used after OpenClaw migration to detect which sections can be skipped.
    ``get_env_value`` is the module-level import from hermes_cli.config
    so that test patches on ``setup_mod.get_env_value`` take effect.
    """
    if section_key == "model":
        if not _model_section_has_credentials(config):
            return None
        model = config.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        if isinstance(model, dict):
            return str(model.get("default") or model.get("model") or "configured")
        return "configured"

    elif section_key == "terminal":
        backend = cfg_get(config, "terminal", "backend", default="local")
        return f"backend: {backend}"

    elif section_key == "agent":
        max_turns = cfg_get(config, "agent", "max_turns", default=90)
        return f"max turns: {max_turns}"

    elif section_key == "gateway":
        from hermes_cli.gateway import _all_platforms, _platform_status
        # Count any non-empty status other than the "not configured" sentinel —
        # platforms like WhatsApp ("enabled, not paired"), Matrix ("configured
        # + E2EE"), and Signal ("partially configured") all indicate the user
        # has already started setup and we shouldn't force the section to rerun.
        configured = [
            _gateway_platform_short_label(plat["label"])
            for plat in _all_platforms()
            if _platform_status(plat) and _platform_status(plat) != "not configured"
        ]
        if configured:
            return ", ".join(configured)
        return None  # No platforms configured — section must run

    elif section_key == "tools":
        tools = []
        if get_env_value("ELEVENLABS_API_KEY"):
            tools.append("TTS/ElevenLabs")
        if get_env_value("BROWSERBASE_API_KEY"):
            tools.append("Browser")
        if get_env_value("FIRECRAWL_API_KEY"):
            tools.append("Firecrawl")
        if tools:
            return ", ".join(tools)
        return None

    return None


def _skip_configured_section(
    config: dict, section_key: str, label: str
) -> bool:
    """Show an already-configured section summary and offer to skip.

    Returns True if the user chose to skip, False if the section should run.
    """
    summary = _get_section_config_summary(config, section_key)
    if not summary:
        return False
    print()
    print_success(f"  {label}: {summary}")
    return not prompt_yes_no(f"  Reconfigure {label.lower()}?", default=False)


# =============================================================================
# OpenClaw Migration
# =============================================================================


_OPENCLAW_SCRIPT = (
    get_optional_skills_dir(PROJECT_ROOT / "optional-skills")
    / "migration"
    / "openclaw-migration"
    / "scripts"
    / "openclaw_to_hermes.py"
)


def _load_openclaw_migration_module():
    """Load the openclaw_to_hermes migration script as a module.

    Returns the loaded module, or None if the script can't be loaded.
    """
    if not _OPENCLAW_SCRIPT.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "openclaw_to_hermes", _OPENCLAW_SCRIPT
    )
    if spec is None or spec.loader is None:
        return None

    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve the module
    # (Python 3.11+ requires this for dynamically loaded modules)
    import sys as _sys
    _sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        _sys.modules.pop(spec.name, None)
        raise
    return mod


# Item kinds that represent high-impact changes warranting explicit warnings.
# Gateway tokens/channels can hijack messaging platforms from the old agent.
# Config values may have different semantics between OpenClaw and Hermes.
# Instruction/context files (.md) can contain incompatible setup procedures.
_HIGH_IMPACT_KIND_KEYWORDS = {
    "gateway": "⚠ Gateway/messaging — this will configure Hermes to use your OpenClaw messaging channels",
    "telegram": "⚠ Telegram — this will point Hermes at your OpenClaw Telegram bot",
    "slack": "⚠ Slack — this will point Hermes at your OpenClaw Slack workspace",
    "discord": "⚠ Discord — this will point Hermes at your OpenClaw Discord bot",
    "whatsapp": "⚠ WhatsApp — this will point Hermes at your OpenClaw WhatsApp connection",
    "config": "⚠ Config values — OpenClaw settings may not map 1:1 to Hermes equivalents",
    "soul": "⚠ Instruction file — may contain OpenClaw-specific setup/restart procedures",
    "memory": "⚠ Memory/context file — may reference OpenClaw-specific infrastructure",
    "context": "⚠ Context file — may contain OpenClaw-specific instructions",
}


def _print_migration_preview(report: dict):
    """Print a detailed dry-run preview of what migration would do.

    Groups items by category and adds explicit warnings for high-impact
    changes like gateway token takeover and config value differences.
    """
    items = report.get("items", [])
    if not items:
        print_info("Nothing to migrate.")
        return

    migrated_items = [i for i in items if i.get("status") == "migrated"]
    conflict_items = [i for i in items if i.get("status") == "conflict"]
    skipped_items = [i for i in items if i.get("status") == "skipped"]

    warnings_shown = set()

    if migrated_items:
        print(color("  Would import:", Colors.GREEN))
        for item in migrated_items:
            kind = item.get("kind", "unknown")
            dest = item.get("destination", "")
            if dest:
                dest_short = str(dest).replace(str(Path.home()), "~")
                print(f"      {kind:<22s} → {dest_short}")
            else:
                print(f"      {kind}")

            # Check for high-impact items and collect warnings
            kind_lower = kind.lower()
            dest_lower = str(dest).lower()
            for keyword, warning in _HIGH_IMPACT_KIND_KEYWORDS.items():
                if keyword in kind_lower or keyword in dest_lower:
                    warnings_shown.add(warning)
        print()

    if conflict_items:
        print(color("  Would overwrite (conflicts with existing Hermes config):", Colors.YELLOW))
        for item in conflict_items:
            kind = item.get("kind", "unknown")
            reason = item.get("reason", "already exists")
            print(f"      {kind:<22s}  {reason}")
        print()

    if skipped_items:
        print(color("  Would skip:", Colors.DIM))
        for item in skipped_items:
            kind = item.get("kind", "unknown")
            reason = item.get("reason", "")
            print(f"      {kind:<22s}  {reason}")
        print()

    # Print collected warnings
    if warnings_shown:
        print(color("  ── Warnings ──", Colors.YELLOW))
        for warning in sorted(warnings_shown):
            print(color(f"    {warning}", Colors.YELLOW))
        print()
        print(color("  Note: OpenClaw config values may have different semantics in Hermes.", Colors.YELLOW))
        print(color("  For example, OpenClaw's tool_call_execution: \"auto\" ≠ Hermes's yolo mode.", Colors.YELLOW))
        print(color("  Instruction files (.md) from OpenClaw may contain incompatible procedures.", Colors.YELLOW))
        print()


def _offer_openclaw_migration(hermes_home: Path) -> bool:
    """Detect ~/.openclaw and offer to migrate during first-time setup.

    Runs a dry-run first to show the user exactly what would be imported,
    overwritten, or taken over. Only executes after explicit confirmation.

    Returns True if migration ran successfully, False otherwise.
    """
    openclaw_dir = Path.home() / ".openclaw"
    if not openclaw_dir.is_dir():
        return False

    if not _OPENCLAW_SCRIPT.exists():
        return False

    print()
    print_header("Обнаружена установка OpenClaw")
    print_info(f"Найдены данные OpenClaw в {openclaw_dir}")
    print_info("Hermes может показать что будет импортировано перед внесением любых изменений.")
    print()

    if not prompt_yes_no("Хотите увидеть что можно импортировать?", default=True):
        print_info(
            "Пропускаем миграцию. Вы можете запустить её позже через: hermes claw migrate --dry-run"
        )
        return False

    # Ensure config.yaml exists before migration tries to read it
    config_path = get_config_path()
    if not config_path.exists():
        save_config(load_config())

    # Load the migration module
    try:
        mod = _load_openclaw_migration_module()
        if mod is None:
            print_warning("Could not load migration script.")
            return False
    except Exception as e:
        print_warning(f"Could not load migration script: {e}")
        logger.debug("OpenClaw migration module load error", exc_info=True)
        return False

    # ── Phase 1: Dry-run preview ──
    try:
        selected = mod.resolve_selected_options(None, None, preset="full")
        dry_migrator = mod.Migrator(
            source_root=openclaw_dir.resolve(),
            target_root=hermes_home.resolve(),
            execute=False,  # dry-run — no files modified
            workspace_target=None,
            overwrite=True,  # show everything including conflicts
            migrate_secrets=True,
            output_dir=None,
            selected_options=selected,
            preset_name="full",
        )
        preview_report = dry_migrator.migrate()
    except Exception as e:
        print_warning(f"Migration preview failed: {e}")
        logger.debug("OpenClaw migration preview error", exc_info=True)
        return False

    # Display the full preview
    preview_summary = preview_report.get("summary", {})
    preview_count = preview_summary.get("migrated", 0)

    if preview_count == 0:
        print()
        print_info("Nothing to import from OpenClaw.")
        return False

    print()
    print_header(f"Migration Preview — {preview_count} item(s) would be imported")
    print_info("No changes have been made yet. Review the list below:")
    print()
    _print_migration_preview(preview_report)

    # ── Phase 2: Confirm and execute ──
    if not prompt_yes_no("Proceed with migration?", default=False):
        print_info(
            "Migration cancelled. You can run it later with: hermes claw migrate"
        )
        print_info(
            "Use --dry-run to preview again, or --preset minimal for a lighter import."
        )
        return False

    # Execute the migration — overwrite=False so existing Hermes configs are
    # preserved. The user saw the preview; conflicts are skipped by default.
    try:
        migrator = mod.Migrator(
            source_root=openclaw_dir.resolve(),
            target_root=hermes_home.resolve(),
            execute=True,
            workspace_target=None,
            overwrite=False,  # preserve existing Hermes config
            migrate_secrets=True,
            output_dir=None,
            selected_options=selected,
            preset_name="full",
        )
        report = migrator.migrate()
    except Exception as e:
        print_warning(f"Migration failed: {e}")
        logger.debug("OpenClaw migration error", exc_info=True)
        return False

    # Print final summary
    summary = report.get("summary", {})
    migrated = summary.get("migrated", 0)
    skipped = summary.get("skipped", 0)
    conflicts = summary.get("conflict", 0)
    errors = summary.get("error", 0)

    print()
    if migrated:
        print_success(f"Imported {migrated} item(s) from OpenClaw.")
    if conflicts:
        print_info(f"Skipped {conflicts} item(s) that already exist in Hermes (use hermes claw migrate --overwrite to force).")
    if skipped:
        print_info(f"Skipped {skipped} item(s) (not found or unchanged).")
    if errors:
        print_warning(f"{errors} item(s) had errors — check the migration report.")

    output_dir = report.get("output_dir")
    if output_dir:
        print_info(f"Full report saved to: {output_dir}")

    print_success("Migration complete! Continuing with setup...")
    return True


# =============================================================================
# Main Wizard Orchestrator
# =============================================================================

SETUP_SECTIONS = [
    ("model", "Model & Provider", setup_model_provider),
    ("tts", "Text-to-Speech", setup_tts),
    ("terminal", "Terminal Backend", setup_terminal_backend),
    ("gateway", "Messaging Platforms (Gateway)", setup_gateway),
    ("tools", "Tools", setup_tools),
    ("agent", "Agent Settings", setup_agent_settings),
]


def run_setup_wizard(args):
    """Run the interactive setup wizard.

    Supports full, quick, and section-specific setup:
      hermes setup           — full or quick (auto-detected)
      hermes setup model     — just model/provider
      hermes setup tts       — just text-to-speech
      hermes setup terminal  — just terminal backend
      hermes setup gateway   — just messaging platforms
      hermes setup tools     — just tool configuration
      hermes setup agent     — just agent settings
    """
    from hermes_cli.config import is_managed, managed_error
    if is_managed():
        managed_error("run setup wizard")
        return
    ensure_hermes_home()

    reset_requested = bool(getattr(args, "reset", False))
    if reset_requested:
        save_config(copy.deepcopy(DEFAULT_CONFIG))
        print_success("Configuration reset to defaults.")

    reconfigure_requested = bool(getattr(args, "reconfigure", False))
    quick_requested = bool(getattr(args, "quick", False))

    config = load_config()
    hermes_home = get_hermes_home()

    # Back up existing config before setup modifies it (#3522)
    config_path = get_config_path()
    if config_path.exists():
        from datetime import datetime as _dt
        _backup_path = config_path.with_suffix(
            f".yaml.bak.{_dt.now().strftime('%Y%m%d_%H%M%S')}"
        )
        try:
            import shutil
            shutil.copy2(config_path, _backup_path)
        except Exception:
            _backup_path = None
    else:
        _backup_path = None

    # Detect non-interactive environments (headless SSH, Docker, CI/CD)
    non_interactive = getattr(args, 'non_interactive', False)
    if not non_interactive and not is_interactive_stdin():
        non_interactive = True

    if non_interactive:
        print_noninteractive_setup_guidance(
            "Running in a non-interactive environment (no TTY detected)."
        )
        return

    # Check if a specific section was requested
    section = getattr(args, "section", None)
    if section:
        for key, label, func in SETUP_SECTIONS:
            if key == section:
                print()
                print(
                    color(
                        "┌─────────────────────────────────────────────────────────┐",
                        Colors.MAGENTA,
                    )
                )
                print(color(f"│     ⚕ Hermes Setup — {label:<34s} │", Colors.MAGENTA))
                print(
                    color(
                        "└─────────────────────────────────────────────────────────┘",
                        Colors.MAGENTA,
                    )
                )
                func(config)
                save_config(config)
                print()
                print_success(f"{label} configuration complete!")
                return

        print_error(f"Unknown setup section: {section}")
        print_info(f"Available sections: {', '.join(k for k, _, _ in SETUP_SECTIONS)}")
        return

    # Check if this is an existing installation with a provider configured
    from hermes_cli.auth import get_active_provider

    active_provider = get_active_provider()
    is_existing = (
        bool(get_env_value("OPENROUTER_API_KEY"))
        or bool(get_env_value("OPENAI_BASE_URL"))
        or active_provider is not None
    )

    print()
    print(
        color(
            "┌─────────────────────────────────────────────────────────┐",
            Colors.MAGENTA,
        )
    )
    print(
        color(
            "│             ⚕ Мастер настройки Hermes Agent           │", Colors.MAGENTA
        )
    )
    print(
        color(
            "├─────────────────────────────────────────────────────────┤",
            Colors.MAGENTA,
        )
    )
    print(
        color(
            "│  Давайте настроим вашу установку Hermes Agent.       │", Colors.MAGENTA
        )
    )
    print(
        color(
            "│  Нажмите Ctrl+C в любое время для выхода.            │", Colors.MAGENTA
        )
    )
    print(
        color(
            "└─────────────────────────────────────────────────────────┘",
            Colors.MAGENTA,
        )
    )

    migration_ran = False

    if is_existing:
        # Existing install — default is the full-wizard reconfigure flow.
        # Every prompt shows the current value as its default, so pressing
        # Enter keeps it.  Opt into `--quick` for the narrow "just fill in
        # missing items" flow (useful after a partial OpenClaw migration
        # or when a required API key got cleared).
        if quick_requested:
            _run_quick_setup(config, hermes_home)
            return

        print()
        print_header("Перенастроить")
        print_success("У вас уже настроен Hermes.")
        print_info("Запускаем полный мастер — каждый запрос показывает текущее значение.")
        print_info("Нажмите Enter чтобы оставить, или введите новое значение.")
        print_info("")
        print_info("Совет: перейдите сразу к разделу через 'hermes setup model|terminal|")
        print_info("     gateway|tools|agent', или настройте только отсутствующие элементы через --quick.")
        # Fall through to the "Full Setup — run all sections" block below.
        # --reconfigure is now the default on existing installs; the flag
        # is preserved for backwards compatibility but is a no-op here.
    else:
        # ── First-Time Setup ──
        print()

        # --reconfigure / --quick on a fresh install are meaningless — fall
        # through to the normal first-time flow.
        if reconfigure_requested or quick_requested:
            print_info("Конфигурация не найдена — запускаем первоначальную настройку.")
            print()

        # Offer OpenClaw migration before configuration begins
        migration_ran = _offer_openclaw_migration(hermes_home)
        if migration_ran:
            config = load_config()

        setup_mode = prompt_choice("Как вы хотите настроить Hermes?", [
            "Быстрая настройка — провайдер, модель и сообщения (рекомендуется)",
            "Полная настройка — настроить всё",
        ], 0)

        if setup_mode == 0:
            _run_first_time_quick_setup(config, hermes_home, is_existing)
            return

    # ── Full Setup — run all sections ──
    print_header("Расположение конфигурации")
    print_info(f"Файл конфигурации:  {get_config_path()}")
    print_info(f"Файл секретов: {get_env_path()}")
    print_info(f"Папка данных:  {hermes_home}")
    print_info(f"Папка установки:  {PROJECT_ROOT}")
    print()
    print_info("Вы можете редактировать эти файлы напрямую или использовать 'hermes config edit'")

    if migration_ran:
        print()
        print_info("Настройки импортированы из OpenClaw.")
        print_info("Each section below will show what was imported — press Enter to keep,")
        print_info("or choose to reconfigure if needed.")

    # Section 1: Model & Provider
    if not (migration_ran and _skip_configured_section(config, "model", "Model & Provider")):
        setup_model_provider(config)

    # Section 2: Terminal Backend
    if not (migration_ran and _skip_configured_section(config, "terminal", "Terminal Backend")):
        setup_terminal_backend(config)

    # Section 3: Agent Settings
    if not (migration_ran and _skip_configured_section(config, "agent", "Agent Settings")):
        setup_agent_settings(config)

    # Section 4: Messaging Platforms
    if not (migration_ran and _skip_configured_section(config, "gateway", "Messaging Platforms")):
        setup_gateway(config)

    # Section 5: Tools
    if not (migration_ran and _skip_configured_section(config, "tools", "Tools")):
        setup_tools(config, first_install=not is_existing)

    # Save and show summary
    save_config(config)
    if _backup_path and _backup_path.exists():
        print_info(f"Previous config backed up to: {_backup_path}")
        print_info("If setup changed a value you customized, restore it with:")
        print_info(f"  cp {_backup_path} {config_path}")
    _print_setup_summary(config, hermes_home)


def _run_first_time_quick_setup(config: dict, hermes_home, is_existing: bool):
    """Streamlined first-time setup: provider, model, terminal & messaging.

    Applies sensible defaults for TTS (Edge), agent settings, and tools —
    the user can customize later via ``hermes setup <section>``.
    """
    # Step 1: Model & Provider (essential — skips rotation/vision/TTS)
    setup_model_provider(config, quick=True)

    # Step 2: Terminal Backend — where commands run is a core decision
    setup_terminal_backend(config)

    # Step 3: Apply defaults for everything else
    _apply_default_agent_settings(config)

    save_config(config)

    # Step 4: Offer messaging gateway setup
    print()
    gateway_choice = prompt_choice(
        "Connect a messaging platform? (Telegram, Discord, etc.)",
        [
            "Set up messaging now (recommended)",
            "Skip — set up later with 'hermes setup gateway'",
        ],
        0,
    )

    if gateway_choice == 0:
        setup_gateway(config)
        save_config(config)

    print()
    print_success("Setup complete! You're ready to go.")
    print()
    print_info("  Configure all settings:    hermes setup")
    if gateway_choice != 0:
        print_info("  Connect Telegram/Discord:  hermes setup gateway")
    print()

    _print_setup_summary(config, hermes_home)


def _run_quick_setup(config: dict, hermes_home):
    """Быстрая настройка — настроить только отсутствующие элементы."""
    from hermes_cli.config import (
        get_missing_env_vars,
        get_missing_config_fields,
        check_config_version,
    )

    print()
    print_header("Быстрая настройка — только отсутствующие элементы")

    # Check what's missing
    missing_required = [
        v for v in get_missing_env_vars(required_only=False) if v.get("is_required")
    ]
    missing_optional = [
        v for v in get_missing_env_vars(required_only=False) if not v.get("is_required")
    ]
    missing_config = get_missing_config_fields()
    current_ver, latest_ver = check_config_version()

    has_anything_missing = (
        missing_required
        or missing_optional
        or missing_config
        or current_ver < latest_ver
    )

    if not has_anything_missing:
        print_success("Всё настроено! Нечего делать.")
        print()
        print_info("Запустите 'hermes setup' и выберите 'Полная настройка' для перенастройки,")
        print_info("или выберите конкретный раздел из меню.")
        return

    # Handle missing required env vars
    if missing_required:
        print()
        print_info(f"{len(missing_required)} обязательных настроек отсутствует:")
        for var in missing_required:
            print(f"     • {var['name']}")
        print()

        for var in missing_required:
            print()
            print(color(f"  {var['name']}", Colors.CYAN))
            print_info(f"  {var.get('description', '')}")
            if var.get("url"):
                print_info(f"  Get key at: {var['url']}")

            if var.get("password"):
                value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
            else:
                value = prompt(f"  {var.get('prompt', var['name'])}")

            if value:
                save_env_value(var["name"], value)
                print_success(f"  Saved {var['name']}")
            else:
                print_warning(f"  Skipped {var['name']}")

    # Split missing optional vars by category
    missing_tools = [v for v in missing_optional if v.get("category") == "tool"]
    missing_messaging = [
        v
        for v in missing_optional
        if v.get("category") == "messaging" and not v.get("advanced")
    ]

    # ── Tool API keys (checklist) ──
    if missing_tools:
        print()
        print_header("Tool API Keys")

        checklist_labels = []
        for var in missing_tools:
            tools = var.get("tools", [])
            tools_str = f" → {', '.join(tools[:2])}" if tools else ""
            checklist_labels.append(f"{var.get('description', var['name'])}{tools_str}")

        selected_indices = prompt_checklist(
            "Which tools would you like to configure?",
            checklist_labels,
        )

        for idx in selected_indices:
            var = missing_tools[idx]
            _prompt_api_key(var)

    # ── Messaging platforms (checklist then prompt for selected) ──
    if missing_messaging:
        print()
        print_header("Платформы сообщений")
        print_info("Подключите Hermes к приложениям сообщений чтобы общаться отовсюду.")
        print_info("Вы можете настроить это позже через 'hermes setup gateway'.")

        # Группировка по платформам (сохраняя порядок)
        platform_order = []
        platforms = {}
        for var in missing_messaging:
            name = var["name"]
            if "TELEGRAM" in name:
                plat = "Telegram"
            elif "DISCORD" in name:
                plat = "Discord"
            elif "SLACK" in name:
                plat = "Slack"
            else:
                continue
            if plat not in platforms:
                platform_order.append(plat)
            platforms.setdefault(plat, []).append(var)

        platform_labels = [
            {
                "Telegram": "📱 Telegram",
                "Discord": "💬 Discord",
                "Slack": "💼 Slack",
            }.get(p, p)
            for p in platform_order
        ]

        selected_indices = prompt_checklist(
            "Which platforms would you like to set up?",
            platform_labels,
        )

        for idx in selected_indices:
            plat = platform_order[idx]
            vars_list = platforms[plat]
            emoji = {"Telegram": "📱", "Discord": "💬", "Slack": "💼"}.get(plat, "")
            print()
            print(color(f"  ─── {emoji} {plat} ───", Colors.CYAN))
            print()
            for var in vars_list:
                print_info(f"  {var.get('description', '')}")
                if var.get("url"):
                    print_info(f"  {var['url']}")
                if var.get("password"):
                    value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
                else:
                    value = prompt(f"  {var.get('prompt', var['name'])}")
                if value:
                    save_env_value(var["name"], value)
                    print_success("  ✓ Saved")
                else:
                    print_warning("  Skipped")
                print()

    # Handle missing config fields
    if missing_config:
        print()
        print_info(
            f"Adding {len(missing_config)} new config option(s) with defaults..."
        )
        for field in missing_config:
            print_success(f"  Added {field['key']} = {field['default']}")

        # Update config version
        config["_config_version"] = latest_ver
        save_config(config)

    # Jump to summary
    _print_setup_summary(config, hermes_home)
