# Hermes Agent ☤

**Самосовершенствующийся ИИ-агент от [Nous Research](https://nousresearch.com).** Это единственный агент со встроенным циклом обучения — он создаёт навыки из опыта, улучшает их во время использования, напоминает себе о сохранении знаний, ищет по прошлым разговорам и строит глубокую модель того, кто вы есть, между сессиями. Запустите его на VPS за $5, GPU-кластере или serverless-инфраструктуре, которая стоит почти ничего, когда простаивает. Он не привязан к вашему ноутбуку — общайтесь с ним из Telegram, пока он работает в облачном VM.

Используйте любую модель — [Nous Portal](https://portal.nousresearch.com), [OpenRouter](https://openrouter.ai) (200+ моделей), [NovitaAI](https://novita.ai), [NVIDIA NIM](https://build.nvidia.com) (Nemotron), [Xiaomi MiMo](https://platform.xiaomimo.com), [z.ai/GLM](https://z.ai), [Kimi/Moonshot](https://platform.moonshot.ai), [MiniMax](https://www.minimax.io), [Hugging Face](https://huggingface.co), OpenAI или свой собственный эндпоинт. Переключайтесь через `hermes model` — без изменений кода, без привязки.

<table>
<tr><td><b>Настоящий терминальный интерфейс</b></td><td>Полноценный TUI с многострочным вводом, автодополнением команд, историей разговоров, прерыванием-и-перенаправлением и потоковым выводом инструментов.</td></tr>
<tr><td><b>Работает там, где вы</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal и Email — всё из одного процесса-шлюза. Транскрипция голосовых сообщений, непрерывность разговоров между платформами.</td></tr>
<tr><td><b>Замкнутый цикл обучения</b></td><td>Курируемая агентом память с периодическими напоминаниями. Автономное создание навыков после сложных задач. Навыки самосовершенствуются при использовании. FTS5-поиск по сессиям с LLM-суммаризацией для межсессийного вспоминания. <a href="https://github.com/plastic-labs/honcho">Honcho</a> диалектическое моделирование пользователя. Совместим с открытым стандартом <a href="https://agentskills.io">agentskills.io</a>.</td></tr>
<tr><td><b>Запланированные автоматизации</b></td><td>Встроенный планировщик cron с доставкой в любую платформу. Ежедневные отчёты, ночные бэкапы, недельные аудиты — всё на естественном языке, работает без участия.</td></tr>
<tr><td><b>Делегирует и параллелит</b></td><td>Создаёт изолированных субагентов для параллельных рабочих потоков. Пишет Python-скрипты, вызывающие инструменты через RPC, схлопывая многошаговые пайплайны в ходы без затрат контекста.</td></tr>
<tr><td><b>Работает где угодно, не только на ноутбуке</b></td><td>Семь терминальных бэкендов — local, Docker, SSH, Singularity, Modal, Daytona и Vercel Sandbox. Daytona и Modal предлагают serverless-персистентность — среда агента спит, когда простаивает, и просыпается по требованию, стоя почти ничего между сессиями. Запустите на VPS за $5 или GPU-кластере.</td></tr>
<tr><td><b>Готов к исследованиям</b></td><td>Пакетная генерация траекторий, сжатие траекторий для обучения следующего поколения моделей вызова инструментов.</td></tr>
</table>

---

## Быстрая установка

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### Windows (нативный, PowerShell) — Ранняя бета

> **Внимание:** Нативная поддержка Windows в **ранней бете**. Устанавливается и работает, но не была проверена так же тщательно, как наши пути Linux/macOS/WSL2. Пожалуйста, [сообщайте об ошибках](https://github.com/NousResearch/hermes-agent/issues), когда сталкиваетесь с проблемами. Для самого проверенного пути на Windows сегодня используйте команду выше внутри **WSL2**.

Запустите в PowerShell:

```powershell
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

Установщик делает всё: uv, Python 3.11, Node.js, ffmpeg, **и портативный Git Bash** (MinGit, распакованный в `%LOCALAPPDATA%\hermes\git` — не требует админ-прав, полностью изолирован от любой системной установки Git). Hermes использует этот встроенный Git Bash для запуска shell-команд.

Если у вас уже установлен Git, установщик обнаружит и использует его вместо этого. В противном случае загрузка MinGit (~45MB) — всё, что нужно — он не затронет и не будет мешать любой системной установке Git.

> **Android / Termux:** Проверенный ручной путь документирован в [руководстве Termux](https://hermes-agent.nousresearch.com/docs/getting-started/termux). В Termux Hermes устанавливает курируемый экстракт `.[termux]`, потому что полный экстракт `.[all]` сейчас тянет Android-несовместимые голосовые зависимости.
>
> **Windows:** Нативный Windows поддерживается как **ранняя бета** — PowerShell-однастрочник выше устанавливает всё, но ожидайте шероховатостей и пожалуйста сообщайте об ошибках. Если предпочитаете использовать WSL2 (наш самый проверенный путь для Windows), команда Linux тоже работает там. Нативная установка Windows живёт под `%LOCALAPPDATA%\hermes`; WSL2 устанавливается под `~/.hermes` как на Linux. Единственная функция Hermes, которая сейчас требует конкретно WSL2 — это чат-панель веб-дашборда (использует POSIX PTY — классический CLI и шлюз оба работают нативно).

После установки:

```bash
source ~/.bashrc    # перезагрузить shell (или: source ~/.zshrc)
hermes              # начать разговор!
```

---

## Начало работы

```bash
hermes              # Интерактивный CLI — начать разговор
hermes model        # Выбрать провайдера и модель LLM
hermes tools        # Настроить включённые инструменты
hermes config set   # Установить отдельные значения конфигурации
hermes gateway      # Запустить шлюз сообщений (Telegram, Discord и т.д.)
hermes setup        # Запустить полный мастер настройки (настраивает всё сразу)
hermes claw migrate # Мигрировать с OpenClaw (если пришли с OpenClaw)
hermes update       # Обновиться до последней версии
hermes doctor       # Диагностировать любые проблемы
```

📖 **[Полная документация →](https://hermes-agent.nousresearch.com/docs/)**

## CLI против Сообщений: Быстрая справка

У Hermes две точки входа: запустите terminal UI через `hermes` или запустите шлюз и общайтесь через Telegram, Discord, Slack, WhatsApp, Signal или Email. Как только вы в разговоре, многие slash-команды общие для обоих интерфейсов.

| Действие | CLI | Платформы сообщений |
|---------|-----|---------------------|
| Начать разговор | `hermes` | Запустите `hermes gateway setup` + `hermes gateway start`, затем отправьте сообщение боту |
| Начать свежую сессию | `/new` или `/reset` | `/new` или `/reset` |
| Сменить модель | `/model [провайдер:модель]` | `/model [провайдер:модель]` |
| Установить личность | `/personality [имя]` | `/personality [имя]` |
| Повторить или отменить последний ход | `/retry`, `/undo` | `/retry`, `/undo` |
| Сжать контекст / проверить использование | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| Просмотреть навыки | `/skills` или `/<имя-навыка>` | `/<имя-навыка>` |
| Прервать текущую работу | `Ctrl+C` или отправить новое сообщение | `/stop` или отправить новое сообщение |
| Статус платформы | `/platforms` | `/status`, `/sethome` |

Для полных списков команд смотрите [руководство CLI](https://hermes-agent.nousresearch.com/docs/user-guide/cli) и [руководство Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging).

---

## Документация

Вся документация находится на **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**:

| Раздел | Что покрыто |
|---------|---------------|
| [Быстрый старт](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) | Установка → настройка → первый разговор за 2 минуты |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli) | Команды, ключевые связки, личности, сессии |
| [Конфигурация](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) | Файл конфигурации, провайдеры, модели, все опции |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Безопасность](https://hermes-agent.nousresearch.com/docs/user-guide/security) | Одобрение команд, спаривание DM, изоляция контейнеров |
| [Инструменты и наборы](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) | 40+ инструментов, система наборов инструментов, терминальные бэкенды |
| [Система навыков](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) | Процедурная память, Skills Hub, создание навыков |
| [Память](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) | Персистентная память, профили пользователей, лучшие практики |
| [MCP Интеграция](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) | Подключение любого MCP сервера для расширенных возможностей |
| [Планирование Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) | Запланированные задачи с доставкой в платформы |
| [Файлы контекста](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files) | Контекст проекта, формирующий каждый разговор |
| [Архитектура](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) | Структура проекта, цикл агента, ключевые классы |
| [Внесение вклада](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) | Настройка разработки, PR процесс, стиль кода |
| [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) | Все команды и флаги |
| [Переменные окружения](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) | Полная ссылка env var |

---

## Миграция с OpenClaw

Если вы пришли с OpenClaw, Hermes может автоматически импортировать ваши настройки, воспоминания, навыки и API ключи.

**Во время первоначальной настройки:** Мастер настройки (`hermes setup`) автоматически обнаруживает `~/.openclaw` и предлагает мигрировать перед началом конфигурации.

**В любое время после установки:**

```bash
hermes claw migrate              # Интерактивная миграция (полный пресет)
hermes claw migrate --dry-run    # Предпросмотр того, что будет мигрировано
hermes claw migrate --preset user-data   # Миграция без секретов
hermes claw migrate --overwrite  # Перезаписать существующие конфликты
```

Что импортируется:
- **SOUL.md** — файл персоны
- **Воспоминания** — записи MEMORY.md и USER.md
- **Навыки** — пользовательские навыки → `~/.hermes/skills/openclaw-imports/`
- **Список разрешённых команд** — шаблоны одобрения
- **Настройки сообщений** — конфиги платформ, разрешённые пользователи, рабочий каталог
- **API ключи** — разрешённые секреты (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs)
- **TTS ассеты** — рабочие аудиофайлы
- **Рабочие инструкции** — AGENTS.md (с `--workspace-target`)

Смотрите `hermes claw migrate --help` для всех опций, или используйте навык `openclaw-migration` для интерактивной агент-направляемой миграции с предпросмотром dry-run.

---

## Внесение вклада

Мы приветствуем вклады! Смотрите [Руководство по внесению вклада](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) для настройки разработки, стиля кода и PR процесса.

Быстрый старт для контрибьюторов — клонируйте и используйте `setup-hermes.sh`:

```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
./setup-hermes.sh     # устанавливает uv, создаёт venv, устанавливает .[all], symlink ~/.local/bin/hermes
./hermes              # авто-обнаруживает venv, не нужно `source` сначала
```

Ручной путь (эквивалентно выше):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all,dev]"
scripts/run_tests.sh
```

---

## Сообщество

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP сервер для Hermes и других MCP хостов, с деревьями доступности AT-SPI, вводом Wayland/X11, скриншотами и нацеливанием окон композитора.
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — Community WeChat bridge: Запустите Hermes Agent и OpenClaw на одном аккаунте WeChat.

---

## Лицензия

MIT — смотрите [LICENSE](LICENSE).

Создано [Nous Research](https://nousresearch.com).
