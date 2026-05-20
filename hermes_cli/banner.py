"""Баннер приветствия, ASCII-арт, сводка по скиллам и проверка обновлений для CLI.

Чистые функции отображения без зависимости от состояния HermesCLI.
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from hermes_constants import get_hermes_home
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prompt_toolkit import print_formatted_text as _pt_print
from prompt_toolkit.formatted_text import ANSI as _PT_ANSI

logger = logging.getLogger(__name__)


# =========================================================================
# ANSI-блоки для отображения разговора
# =========================================================================

_GOLD = "\033[1;38;2;255;215;0m"  # True-color #FFD700 bold
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RST = "\033[0m"


def cprint(text: str):
    """Print ANSI-colored text through prompt_toolkit's renderer."""
    _pt_print(_PT_ANSI(text))


# =========================================================================
# Вспомогательные функции для работы со скинами
# =========================================================================

def _skin_color(key: str, fallback: str) -> str:
    """Получить цвет из активного скина или вернуть фолбэк."""
    try:
        from hermes_cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except Exception:
        return fallback


def _skin_branding(key: str, fallback: str) -> str:
    """Получить строку брендинга из активного скина или вернуть фолбэк."""
    try:
        from hermes_cli.skin_engine import get_active_skin
        return get_active_skin().get_branding(key, fallback)
    except Exception:
        return fallback


# =========================================================================
# ASCII-арт и брендинг
# =========================================================================

from hermes_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE

# Импортировать систему переводов
try:
    from hermes_cli.translations import t, is_russian
except ImportError:
    def t(key, default="", **kwargs):
        return default
    def is_russian():
        return False

HERMES_AGENT_LOGO = """[bold #FFD700]██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD700]██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#FFBF00]███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#FFBF00]██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#CD7F32]██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#CD7F32]╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]"""

HERMES_CADUCEUS = """[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⣀⣀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⣇⠸⣿⣿⠇⣸⣿⣿⣷⣦⣄⡀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⢀⣠⣴⣶⠿⠋⣩⡿⣿⡿⠻⣿⡇⢠⡄⢸⣿⠟⢿⣿⢿⣍⠙⠿⣶⣦⣄⡀⠀[/]
[#FFBF00]⠀⠀⠉⠉⠁⠶⠟⠋⠀⠉⠀⢀⣈⣁⡈⢁⣈⣁⡀⠀⠉⠀⠙⠻⠶⠈⠉⠉⠀⠀[/]
[#FFD700]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⡿⠛⢁⡈⠛⢿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFD700]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⣿⣦⣤⣈⠁⢠⣴⣿⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠻⢿⣿⣦⡉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢷⣦⣈⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⠦⠈⠙⠿⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣤⡈⠁⢤⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠷⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠑⢶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠁⢰⡆⠈⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⠈⣡⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]"""



# =========================================================================
# Сканирование скиллов
# =========================================================================

def get_available_skills() -> Dict[str, List[str]]:
    """Вернуть скиллы, сгруппированные по категориям, с фильтрацией по платформе и отключённому состоянию.

    Делегирует ``_find_all_skills()`` из ``tools/skills_tool``, который уже
    обрабатывает фильтрацию по платформе (``platforms:`` во фронтматтере) и учитывает
    пользовательский список ``skills.disabled`` из конфига.
    """
    try:
        from tools.skills_tool import _find_all_skills
        all_skills = _find_all_skills()  # already filtered
    except Exception:
        return {}

    skills_by_category: Dict[str, List[str]] = {}
    for skill in all_skills:
        category = skill.get("category") or "general"
        skills_by_category.setdefault(category, []).append(skill["name"])
    return skills_by_category


# =========================================================================
# Проверка обновлений
# =========================================================================

# Кэшировать результаты проверки обновлений в течение 6 часов, чтобы избежать повторных git fetches
_UPDATE_CHECK_CACHE_SECONDS = 6 * 3600

# Sentinel-значение, возвращаемое когда известно, что обновление существует, но не можем посчитать коммиты
# (например, nix-собранный hermes — нет локальной git-истории для подсчёта).
UPDATE_AVAILABLE_NO_COUNT = -1

_UPSTREAM_REPO_URL = "https://github.com/NousResearch/hermes-agent.git"


def _check_via_rev(local_rev: str) -> Optional[int]:
    """Сравнить встроенную git-ревизию с upstream main через ls-remote.

    Возвращает 0 если актуально, ``UPDATE_AVAILABLE_NO_COUNT`` если отстали,
    или ``None`` при ошибке.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", _UPSTREAM_REPO_URL, "refs/heads/main"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    upstream_rev = result.stdout.split()[0]
    if not upstream_rev:
        return None
    return 0 if upstream_rev == local_rev else UPDATE_AVAILABLE_NO_COUNT


def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Посчитать коммиты отставания от origin/main в локальном checkout."""
    try:
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            capture_output=True, timeout=10,
            cwd=str(repo_dir),
        )
    except Exception:
        pass  # Оффлайн или таймаут — использовать stale refs, это нормально

    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def _version_tuple(v: str) -> tuple[int, ...]:
    """Разобрать '0.13.0' в (0, 13, 0) для сравнения. Ненумерические сегменты становятся 0."""
    parts = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _fetch_pypi_latest(package: str = "hermes-agent") -> Optional[str]:
    """Получить последнюю версию пакета из PyPI. Возвращает None при ошибке."""
    try:
        import urllib.request
        url = f"https://pypi.org/pypi/{package}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("info", {}).get("version")
    except Exception:
        return None


def check_via_pypi() -> Optional[int]:
    """Сравнить установленную версию с последней из PyPI.

    Возвращает 0 если актуально, 1 если отстали, None при ошибке.
    """
    latest = _fetch_pypi_latest()
    if latest is None:
        return None
    if latest == VERSION:
        return 0
    try:
        if _version_tuple(latest) > _version_tuple(VERSION):
            return 1
        return 0
    except Exception:
        return 1 if latest != VERSION else 0


def check_for_updates() -> Optional[int]:
    """Проверить, доступно ли обновление Hermes.

    Два пути: если ``HERMES_REVISION`` установлен (nix-сборки встраивают его),
    сравниваем его с upstream main через ``git ls-remote``. Иначе ищем локальный
    git checkout и считаем коммиты отставания от ``origin/main``.

    Возвращает число коммитов отставания, ``UPDATE_AVAILABLE_NO_COUNT`` (-1)
    если отстали, но счёт неизвестен, ``0`` если актуально, или ``None`` если
    проверка не удалась или не применима. Кэшируется на 6 часов.
    """
    hermes_home = get_hermes_home()
    cache_file = hermes_home / ".update_check"
    embedded_rev = os.environ.get("HERMES_REVISION") or None

    # Прочитать кэш — аннулировать, если встроенная rev изменилась с момента последней проверки
    now = time.time()
    try:
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if (
                now - cached.get("ts", 0) < _UPDATE_CHECK_CACHE_SECONDS
                and cached.get("rev") == embedded_rev
            ):
                return cached.get("behind")
    except Exception:
        pass

    if embedded_rev:
        behind = _check_via_rev(embedded_rev)
    else:
        # Предпочитать расположение работающего кода профильному пути,
        # потому что ``$HERMES_HOME/hermes-agent/`` может быть устаревшей копией
        # из --clone-all.
        # Path(__file__) всегда разрешается в фактический установленный checkout.
        repo_dir = Path(__file__).parent.parent.resolve()
        if not (repo_dir / ".git").exists():
            repo_dir = hermes_home / "hermes-agent"
        if not (repo_dir / ".git").exists():
            behind = check_via_pypi()
        else:
            behind = _check_via_local_git(repo_dir)

    try:
        cache_file.write_text(json.dumps({"ts": now, "behind": behind, "rev": embedded_rev}))
    except Exception:
        pass

    return behind


def _resolve_repo_dir() -> Optional[Path]:
    """Вернуть активный git checkout Hermes или None, если это не git-установка.

    Предпочитает расположение работающего кода профильному пути,
    потому что ``$HERMES_HOME/hermes-agent/`` может быть устаревшей копией
    из --clone-all.
    """
    repo_dir = Path(__file__).parent.parent.resolve()
    if not (repo_dir / ".git").exists():
        hermes_home = get_hermes_home()
        repo_dir = hermes_home / "hermes-agent"
    return repo_dir if (repo_dir / ".git").exists() else None


def _git_short_hash(repo_dir: Path, rev: str) -> Optional[str]:
    """Разрешить git-ревизию в 8-символьный короткий хэш."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", rev],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    return value or None


def get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    """Вернуть хэши upstream/local git для баннера при запуске."""
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        return None

    upstream = _git_short_hash(repo_dir, "origin/main")
    local = _git_short_hash(repo_dir, "HEAD")
    if not upstream or not local:
        return None

    ahead = 0
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            ahead = int((result.stdout or "0").strip() or "0")
    except Exception:
        ahead = 0

    return {"upstream": upstream, "local": local, "ahead": max(ahead, 0)}


_RELEASE_URL_BASE = "https://github.com/NousResearch/hermes-agent/releases/tag"
_latest_release_cache: Optional[tuple] = None  # (tag, url) once resolved


def get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]:
    """Вернуть ``(tag, release_url)`` для последнего git-тега или None.

    Локально — запускает ``git describe --tags --abbrev=0`` в checkout Hermes.
    Кэшируется на процесс. Release URL всегда указывает на каноничный
    NousResearch/hermes-agent репозиторий (форки не получают ссылку).
    """
    global _latest_release_cache
    if _latest_release_cache is not None:
        return _latest_release_cache or None

    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        _latest_release_cache = ()  # falsy sentinel — skip future lookups
        return None

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=str(repo_dir),
        )
    except Exception:
        _latest_release_cache = ()
        return None

    if result.returncode != 0:
        _latest_release_cache = ()
        return None

    tag = (result.stdout or "").strip()
    if not tag:
        _latest_release_cache = ()
        return None

    url = f"{_RELEASE_URL_BASE}/{tag}"
    _latest_release_cache = (tag, url)
    return _latest_release_cache


def format_banner_version_label() -> str:
    """Вернуть метку версии, показываемую в заголовке баннера при запуске."""
    base = f"Hermes Agent v{VERSION} ({RELEASE_DATE})"
    state = get_git_banner_state()
    if not state:
        return base

    upstream = state["upstream"]
    local = state["local"]
    ahead = int(state.get("ahead") or 0)

    if ahead <= 0 or upstream == local:
        return f"{base} · upstream {upstream}"

    carried_word = "commit" if ahead == 1 else "commits"
    return f"{base} · upstream {upstream} · local {local} (+{ahead} carried {carried_word})"


# =========================================================================
# Неблокирующая проверка обновлений
# =========================================================================

_update_result: Optional[int] = None
_update_check_done = threading.Event()


def prefetch_update_check():
    """Запустить проверку обновлений в фоновом daemon-потоке."""
    def _run():
        global _update_result
        _update_result = check_for_updates()
        _update_check_done.set()
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def get_update_result(timeout: float = 0.5) -> Optional[int]:
    """Получить результат предварительной проверки. Возвращает None если не готово."""
    _update_check_done.wait(timeout=timeout)
    return _update_result


# =========================================================================
# Баннер приветствия
# =========================================================================

def _format_context_length(tokens: int) -> str:
    """Форматировать количество токенов для отображения (например, 128000 → '128K', 1048576 → '1M')."""
    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}M"
        return f"{val:.1f}M"
    elif tokens >= 1_000:
        val = tokens / 1_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}K"
        return f"{val:.1f}K"
    return str(tokens)


def _display_toolset_name(toolset_name: str) -> str:
    """Нормализовать внутренние/устаревшие идентификаторы тулсетов для отображения в баннере."""
    if not toolset_name:
        return "unknown"
    return (
        toolset_name[:-6]
        if toolset_name.endswith("_tools")
        else toolset_name
    )


def build_welcome_banner(console: Console, model: str, cwd: str,
                         tools: List[dict] = None,
                         enabled_toolsets: List[str] = None,
                         session_id: str = None,
                         get_toolset_for_tool=None,
                         context_length: int = None):
    """Построить и вывести баннер приветствия с кадукеем слева и информацией справа.

    Args:
        console: Rich Console instance.
        model: Текущее имя модели.
        cwd: Текущая рабочая директория.
        tools: Список определений инструментов.
        enabled_toolsets: Список включённых тулсетов.
        session_id: Идентификатор сессии.
        get_toolset_for_tool: Callable для маппинга имени инструмента -> имя тулсета.
        context_length: Размер контекстного окна модели в токенах.
    """
    from model_tools import check_tool_availability, TOOLSET_REQUIREMENTS
    if get_toolset_for_tool is None:
        from model_tools import get_toolset_for_tool

    tools = tools or []
    enabled_toolsets = enabled_toolsets or []

    _, unavailable_toolsets = check_tool_availability(quiet=True)
    disabled_tools = set()
    # Инструменты, чей тулсет имеет check_fn, лениво инициализируются (например, honcho,
    # homeassistant) — они показываются как недоступные во время баннера, потому что
    # проверка ещё не запустилась, но они не misconfigured.
    lazy_tools = set()
    for item in unavailable_toolsets:
        toolset_name = item.get("name", "")
        ts_req = TOOLSET_REQUIREMENTS.get(toolset_name, {})
        tools_in_ts = item.get("tools", [])
        if ts_req.get("check_fn"):
            lazy_tools.update(tools_in_ts)
        else:
            disabled_tools.update(tools_in_ts)

    layout_table = Table.grid(padding=(0, 2))
    layout_table.add_column("left", justify="center")
    layout_table.add_column("right", justify="left")

    # Разрешить цвета скина один раз для всего баннера
    accent = _skin_color("banner_accent", "#FFBF00")
    dim = _skin_color("banner_dim", "#B8860B")
    text = _skin_color("banner_text", "#FFF8DC")
    session_color = _skin_color("session_border", "#8B8682")

    # Использование скина для кастомного кадуцея
    try:
        from hermes_cli.skin_engine import get_active_skin
        _bskin = get_active_skin()
        _hero = _bskin.banner_hero if hasattr(_bskin, 'banner_hero') and _bskin.banner_hero else HERMES_CADUCEUS
    except Exception:
        _bskin = None
        _hero = HERMES_CADUCEUS
    left_lines = ["", _hero, ""]
    model_short = model.split("/")[-1] if "/" in model else model
    if model_short.endswith(".gguf"):
        model_short = model_short[:-5]
    if len(model_short) > 28:
        model_short = model_short[:25] + "..."
    ctx_str = f" [dim {dim}]·[/] [dim {dim}]{_format_context_length(context_length)} {t('BANNER.context', 'контекст')}[/]" if context_length else ""
    left_lines.append(f"[{accent}]{model_short}[/]{ctx_str} [dim {dim}]·[/] [dim {dim}]{t('BANNER.nous_research', 'Nous Research')}[/]")

    if os.getenv("HERMES_YOLO_MODE"):
        left_lines.append(f"[bold red]⚠ {t('BANNER.yolo_mode', 'Режим YOLO')}[/] [dim {dim}]{t('BANNER.yolo_mode_desc', '— все подтверждения bypassed')}[/]")
    left_lines.append(f"[dim {dim}]{cwd}[/]")
    if session_id:
        left_lines.append(f"[dim {session_color}]{t('BANNER.session', 'Сессия')}: {session_id}[/]")
    left_content = "\n".join(left_lines)

    # Строки с поддержкой перевода
    tools_title = t("BANNER.available_tools", "Доступные инструменты")
    skills_title = t("BANNER.available_skills", "Доступные навыки")
    mcp_title = t("BANNER.mcp_servers", "MCP серверы")
    runtime_label = t("BANNER.runtime", "Среда выполнения")
    profile_label = t("BANNER.profile", "Профиль")
    no_skills = t("BANNER.no_skills", "Навыки не установлены")
    and_more_toolsets = t("BANNER.and_more_toolsets", "(и ещё {count} наборов инструментов...)")
    failed = t("BANNER.failed", "ошибка")
    help_hint = t("BANNER.help_hint", "/help для команд")
    tools_word = t("BANNER.tools", "инструменты")
    skills_word = t("BANNER.skills", "навыки")
    servers_word = t("BANNER.servers", "серверы")
    
    right_lines = [f"[bold {accent}]{tools_title}[/]"]
    toolsets_dict: Dict[str, list] = {}

    for tool in tools:
        tool_name = tool["function"]["name"]
        toolset = _display_toolset_name(get_toolset_for_tool(tool_name) or "other")
        toolsets_dict.setdefault(toolset, []).append(tool_name)

    for item in unavailable_toolsets:
        toolset_id = item.get("id", item.get("name", "unknown"))
        display_name = _display_toolset_name(toolset_id)
        if display_name not in toolsets_dict:
            toolsets_dict[display_name] = []
        for tool_name in item.get("tools", []):
            if tool_name not in toolsets_dict[display_name]:
                toolsets_dict[display_name].append(tool_name)

    sorted_toolsets = sorted(toolsets_dict.keys())
    display_toolsets = sorted_toolsets[:8]
    remaining_toolsets = len(sorted_toolsets) - 8

    for toolset in display_toolsets:
        tool_names = toolsets_dict[toolset]
        colored_names = []
        for name in sorted(tool_names):
            if name in disabled_tools:
                colored_names.append(f"[red]{name}[/]")
            elif name in lazy_tools:
                colored_names.append(f"[yellow]{name}[/]")
            else:
                colored_names.append(f"[{text}]{name}[/]")

        tools_str = ", ".join(colored_names)
        if len(", ".join(sorted(tool_names))) > 45:
            short_names = []
            length = 0
            for name in sorted(tool_names):
                if length + len(name) + 2 > 42:
                    short_names.append("...")
                    break
                short_names.append(name)
                length += len(name) + 2
            colored_names = []
            for name in short_names:
                if name == "...":
                    colored_names.append("[dim]...[/]")
                elif name in disabled_tools:
                    colored_names.append(f"[red]{name}[/]")
                elif name in lazy_tools:
                    colored_names.append(f"[yellow]{name}[/]")
                else:
                    colored_names.append(f"[{text}]{name}[/]")
            tools_str = ", ".join(colored_names)

        right_lines.append(f"[dim {dim}]{toolset}:[/] {tools_str}")

    if remaining_toolsets > 0:
        right_lines.append(f"[dim {dim}]{and_more_toolsets.format(count=remaining_toolsets)}[/]")

    # Секция MCP серверов (только если настроены)
    try:
        from tools.mcp_tool import get_mcp_status
        mcp_status = get_mcp_status()
    except Exception:
        mcp_status = []

    if mcp_status:
        right_lines.append("")
        right_lines.append(f"[bold {accent}]{mcp_title}[/]")
        for srv in mcp_status:
            if srv["connected"]:
                right_lines.append(
                    f"[dim {dim}]{srv['name']}[/] [{text}]({srv['transport']})[/] "
                    f"[dim {dim}]—[/] [{text}]{srv['tools']} {servers_word}[/]"
                )
            else:
                right_lines.append(
                    f"[red]{srv['name']}[/] [dim]({srv['transport']})[/] "
                    f"[red]— {failed}[/]"
                )

    right_lines.append("")
    right_lines.append(f"[bold {accent}]{skills_title}[/]")
    skills_by_category = get_available_skills()
    total_skills = sum(len(s) for s in skills_by_category.values())

    if skills_by_category:
        for category in sorted(skills_by_category.keys()):
            skill_names = sorted(skills_by_category[category])
            if len(skill_names) > 8:
                display_names = skill_names[:8]
                skills_str = ", ".join(display_names) + " " + t("BANNER.and_more", "+{count} ещё").format(count=len(skill_names) - 8)
            else:
                skills_str = ", ".join(skill_names)
            if len(skills_str) > 50:
                skills_str = skills_str[:47] + "..."
            right_lines.append(f"[dim {dim}]{category}:[/] [{text}]{skills_str}[/]")
    else:
        right_lines.append(f"[dim {dim}]{no_skills}[/]")

    right_lines.append("")
    mcp_connected = sum(1 for s in mcp_status if s["connected"]) if mcp_status else 0
    summary_parts = [f"{len(tools)} {tools_word}", f"{total_skills} {skills_word}"]
    if mcp_connected:
        summary_parts.append(f"{mcp_connected} MCP {servers_word}")
    summary_parts.append(help_hint)
    # Показывать, когда runtime codex_app_server активен, чтобы пользователи
    # понимали, почему количество инструментов может не совпадать с фактически доступными
    # (codex строит свой собственный список инструментов внутри spawned subprocess).
    try:
        from hermes_cli.codex_runtime_switch import get_current_runtime
        from hermes_cli.config import load_config as _load_cfg
        if get_current_runtime(_load_cfg()) == "codex_app_server":
            runtime_text = f"{runtime_label}:" if is_russian() else "Runtime:"
            right_lines.append(
                f"[bold {accent}]{runtime_text}[/] [{text}]codex app-server[/] "
                f"[dim {dim}](terminal/file ops/MCP работают внутри codex)[/]"
            )
    except Exception:
        pass
    # Показать имя активного профиля, если не 'default'
    try:
        from hermes_cli.profiles import get_active_profile_name
        _profile_name = get_active_profile_name()
        if _profile_name and _profile_name != "default":
            profile_text = f"{profile_label}:" if is_russian() else "Profile:"
            right_lines.append(f"[bold {accent}]{profile_text}[/] [{text}]{_profile_name}[/]")
    except Exception:
        pass  # Никогда не ломать баннер из-за бага в profiles.py

    right_lines.append(f"[dim {dim}]{' · '.join(summary_parts)}[/]")

    # Проверка обновлений — использовать результат предварительной проверки
    try:
        behind = get_update_result(timeout=0.5)
        if behind is not None and behind != 0:
            from hermes_cli.config import get_managed_update_command, recommended_update_command
            if behind > 0:
                update_msg = t("BANNER.update_available_commits", "⚠ {count} коммитов позади", count=behind).format(count=behind)
                right_lines.append(
                    f"[bold yellow]{update_msg}[/]"
                    f"[dim yellow] — {t('BANNER.run_to_update', '— выполните {command} для обновления').format(command=recommended_update_command())}[/]"
                )
            else:
                # UPDATE_AVAILABLE_NO_COUNT: nix-собранный hermes; знаем, что обновление
                # существует, но не на сколько, и не знаем, как пользователь установил
                # (nix run, profile, system flake, home-manager).
                managed_cmd = get_managed_update_command()
                line = t("BANNER.update_available", "⚠ доступно обновление")
                if managed_cmd:
                    line += f"[dim yellow] — {t('BANNER.run_to_update', '— выполните {command} для обновления').format(command=managed_cmd)}[/]"
                right_lines.append(line)
    except Exception:
        pass  # Никогда не ломать баннер из-за проверки обновлений

    right_content = "\n".join(right_lines)
    layout_table.add_row(left_content, right_content)

    title_color = _skin_color("banner_title", "#FFD700")
    border_color = _skin_color("banner_border", "#CD7F32")
    version_label = format_banner_version_label()
    release_info = get_latest_release_tag()
    if release_info:
        _tag, _url = release_info
        title_markup = f"[bold {title_color}][link={_url}]{version_label}[/link][/]"
    else:
        title_markup = f"[bold {title_color}]{version_label}[/]"
    outer_panel = Panel(
        layout_table,
        title=title_markup,
        border_style=border_color,
        padding=(0, 2),
    )

    console.print()
    term_width = shutil.get_terminal_size().columns
    if term_width >= 95:
        _logo = _bskin.banner_logo if _bskin and hasattr(_bskin, 'banner_logo') and _bskin.banner_logo else HERMES_AGENT_LOGO
        console.print(_logo)
        console.print()
    console.print(outer_panel)
