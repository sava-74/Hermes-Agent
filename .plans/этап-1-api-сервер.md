# Этап 1: API-сервер (Детальный план)

**Статус:** В работе  
**Версия:** 0.1  
**Дата:** 2026-05-20  
**Связь с генпланом:** `.plans/модернизация-гермес.md` → Этап 1

---

## Цель

Запустить локальный API-сервер с:
- Полным доступом ко всем инструментам Hermes (terminal, file, browser, skills...)
- Режимом "Секретарь" (простое общение)
- Режимом "Консилиум" (спор моделей до DONE)
- WebSocket стримингом ответов
- Запуском как служба Windows (автозапуск)

---

## Архитектура API-сервера

```
┌─────────────────────────────────────────────────────────────────┐
│                    api_server.py                                │
│                    (FastAPI + WebSocket)                        │
│                                                                 │
│  Endpoints:                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ POST /chat          │ Общение (режим секретаря)         │   │
│  │ WebSocket /stream   │ Стриминг ответов                  │   │
│  │ POST /discourse     │ Консилиум моделей (спор до DONE)  │   │
│  │ GET  /tools         │ Список инструментов               │   │
│  │ POST /tools/execute │ Выполнение инструмента            │   │
│  │ GET  /health        │ Проверка статуса                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Компоненты:                                                    │
│  ┌─────────────────┐  ┌──────────────────┐                     │
│  │ LLMDirector     │  │ Hermes AIAgent   │                     │
│  │ (Сверхразум)    │  │ (Гермес)         │                     │
│  │ • Секретарь     │  │ • Tools          │                     │
│  │ • Консилиум     │  │ • Memory         │                     │
│  │ • Матричный     │  │ • Skills         │                     │
│  │   язык          │  │ • Sessions       │                     │
│  └─────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Подзадачи (по порядку)

### 1.1 Изучение инициализации AIAgent

**Файл:** `run_agent.py`

**Что найти:**
- Как создаётся `AIAgent` (параметры `__init__`)
- Какие параметры обязательные, какие опциональные
- Как подключаются инструменты (`enabled_toolsets`)
- Как работает `agent.chat(message)`

**Команды для изучения:**
```bash
# Найти конструктор AIAgent
search_files pattern="class AIAgent" path="D:\GitHub\agent-1"

# Найти метод chat
search_files pattern="def chat" path="D:\GitHub\agent-1\run_agent.py"

# Посмотреть примеры использования
search_files pattern="AIAgent\(" path="D:\GitHub\agent-1" limit=20
```

**Ожидаемый результат:**
```python
# Пример того, что мы ищем:
agent = AIAgent(
    base_url="...",
    api_key="...",
    provider="alibaba",
    model="qwen3.5-plus",
    enabled_toolsets=["terminal", "file", "browser", ...],
    ...
)
response = agent.chat("Привет!")
```

---

### 1.2 Интеграция LLMDirector

**Файл-донор:** `D:\GitHub\agent\core\llm_director.py`

**Что перенести:**
- Класс `LLMDirector` (полностью)
- Метод `get_directed_stream()` — режим секретаря
- Метод `run_ai_discourse()` — режим консилиума
- Промты `LOCAL_SYSTEM` и `CLOUD_SYSTEM` (требуют рефакторинга!)

**Что изменить:**
- Убрать зависимость от `llm_connector` (заменить на Hermes `AIAgent`)
- Убрать зависимость от `cloud_connector` (заменить на прямой API вызов)
- Добавить поддержку WebSocket стриминга

**Ожидаемый результат:**
```python
class LLMDirector:
    def __init__(self, hermes_agent, local_model_connector):
        self.hermes = hermes_agent  # Облако
        self.local = local_model_connector  # Локалка
    
    def get_directed_stream(self, user_request) -> Generator:
        # Режим секретаря: простое → локально, сложное → облако
        ...
    
    async def run_ai_discourse(self, user_prompt, max_turns=5) -> AsyncGenerator:
        # Режим консилиума: спор до DONE
        ...
```

---

### 1.3 Создание api_server.py (FastAPI)

**Файл:** `D:\GitHub\agent-1\api_server.py`

**Структура:**
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

from run_agent import AIAgent
from core.llm_director import LLMDirector  # После интеграции

app = FastAPI(title="Hermes API Server")

# CORS для Chat UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Настроить для продакшена
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация
agent = None
director = None

@app.on_event("startup")
async def startup_event():
    global agent, director
    agent = AIAgent(...)  # Изучить в 1.1
    director = LLMDirector(agent, local_connector=...)

@app.on_event("shutdown")
async def shutdown_event():
    # Очистка ресурсов
    pass

# === ENDPOINTS ===

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent": "ready" if agent else "initializing"}

@app.post("/chat")
async def chat(message: str, session_id: str = None):
    """Режим секретаря: простое общение"""
    response = agent.chat(message)
    return {"response": response, "session_id": session_id}

@app.websocket("/stream")
async def stream_websocket(websocket: WebSocket):
    """WebSocket стриминг ответов"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Стриминг токенами
            async for token in director.get_directed_stream(message["text"]):
                await websocket.send_json({"type": "token", "content": token})
            
            await websocket.send_json({"type": "complete"})
    except WebSocketDisconnect:
        pass

@app.post("/discourse")
async def discourse(prompt: str, max_turns: int = 5):
    """Режим консилиума: спор моделей до DONE"""
    # Запуск консилиума
    ...

@app.get("/tools")
async def list_tools():
    """Список доступных инструментов"""
    return {"tools": agent.get_available_tools()}

@app.post("/tools/execute")
async def execute_tool(tool_name: str, args: dict):
    """Выполнение инструмента"""
    result = agent.execute_tool(tool_name, args)
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

### 1.4 Настройка локальной модели

**Варианты:**
| Движок | Команда | Порт | Примечание |
|--------|---------|------|------------|
| **Ollama** | `ollama serve` | 11434 | Популярно, много моделей |
| **TabbyAPI** | `python main.py` | 5000 | Уже используешь в `main.py` |
| **LM Studio** | GUI → Start Server | 1234 | Удобно, но GUI |
| **llama.cpp** | `./server -m model.gguf` | 8080 | Легковесно |

**Что нужно:**
1. Выбрать движок (предлагаю **TabbyAPI** — ты уже используешь)
2. Настроить автозапуск (служба Windows)
3. Подключить к `LLMDirector.local_connector`

**Конфигурация:**
```python
# config.py
LOCAL_MODEL_CONFIG = {
    "type": "tabbyapi",  # или "ollama", "lmstudio"
    "host": "localhost",
    "port": 5000,
    "model": "qwen-32b",  # или другая
    "api_key": None,  # если требуется
}
```

---

### 1.5 Запуск как служба Windows

**Варианты:**

| Способ | Сложность | Надёжность |
|--------|-----------|------------|
| **NSSM** (Non-Sucking Service Manager) | Низкая | Высокая |
| **Windows Task Scheduler** | Средняя | Средняя |
| **pywin32 Service** | Высокая | Высокая |

**Рекомендую NSSM:**

```powershell
# 1. Скачать NSSM
winget install nssm

# 2. Установить службу API-сервера
nssm install HermesAPI "D:\GitHub\agent-1\.venv\Scripts\python.exe" "D:\GitHub\agent-1\api_server.py"

# 3. Настроить рабочую директорию
nssm set HermesAPI AppDirectory "D:\GitHub\agent-1"

# 4. Настроить переменные окружения
nssm set HermesAPI AppEnvironmentExtra "PATH=%PATH%;D:\GitHub\agent-1\.venv\Scripts"

# 5. Запустить службу
nssm start HermesAPI

# 6. Проверить статус
nssm status HermesAPI
```

**Альтернатива (скрипт):**
```powershell
# scripts/install-service.ps1
$serviceName = "HermesAPI"
$servicePath = "D:\GitHub\agent-1\api_server.py"
$pythonPath = "D:\GitHub\agent-1\.venv\Scripts\python.exe"

# Создать службу через sc.exe
sc.exe create $serviceName binPath= "$pythonPath $servicePath" start= auto
sc.exe description $serviceName "Hermes API Server - локальный ИИ-помощник"
sc.exe start $serviceName
```

---

### 1.6 Рефакторинг промтов Директора

**Проблема:** Ты сказал *"я сейчас немного исправил промт в директоре, стало хуже"*.

**План исправления:**

1. **Вернуться к рабочей версии** (из `llm_director.py` до изменений)
2. **Тестировать итеративно** — маленькими шагами
3. **Логировать всё** — сохранять ответы до/после изменений

**Текущие промты (из кода):**
```python
LOCAL_SYSTEM = (
    "Проанализируй присланный текст/код. Напиши кратко и строго по существу, "
    "какие в нём есть реальные технические ошибки, логические баги или критические упущения. "
    "Не пиши общих слов и вежливых фраз. Если код/текст полностью корректен, эффективен, "
    "безопасен и дорабатывать больше нечего, напиши строго одно слово: DONE"
)

CLOUD_SYSTEM = (
    "Выполни задачу пользователя на русском языке. Пиши сразу чистое, качественное "
    "и готовое решение. Если к твоему прошлому ответу прислали конкретные замечания, "
    "полностью учти их, исправь ошибки и выкати улучшенную финальную версию."
)
```

**Что улучшить:**
- Добавить **конкретные критерии** для DONE (что считать "готовым"?)
- Добавить **тип задачи** (код/текст/архитектура) → разные критерии
- Добавить **ограничения** (максимум итераций, время)

**Новые промты (черновик):**
```python
LOCAL_SYSTEM_CODE = (
    "Ты технический ревьюер. Анализируй код строго по пунктам:\n"
    "1. Синтаксические ошибки\n"
    "2. Логические баги\n"
    "3. Уязвимости безопасности\n"
    "4. Неоптимальности (производительность)\n"
    "5. Нарушения best practices\n\n"
    "Если найдёшь проблемы — перечисли кратко. Если код идеален — напиши ТОЛЬКО: DONE"
)

LOCAL_SYSTEM_TEXT = (
    "Ты логический анализатор. Ищи:\n"
    "1. Фактические ошибки\n"
    "2. Логические противоречия\n"
    "3. Неполноту информации\n\n"
    "Если текст корректен — напиши ТОЛЬКО: DONE"
)
```

---

### 1.7 Кэширование консенсусных ответов

**Проблема:** Каждый запрос запускает дискуссию заново → трата токенов.

**Решение:** Кэшировать по хэшу запроса.

**Реализация:**
```python
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path("cache/consensus")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

def get_from_cache(prompt: str) -> str | None:
    key = get_cache_key(prompt)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("response")
    return None

def save_to_cache(prompt: str, response: str):
    key = get_cache_key(prompt)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt, "response": response}, f, ensure_ascii=False, indent=2)

# Использование в LLMDirector:
async def run_ai_discourse(self, user_prompt, max_turns=5):
    cached = get_from_cache(user_prompt)
    if cached:
        yield cached
        return
    
    # ... запуск консилиума ...
    
    save_to_cache(user_prompt, final_response)
```

---

## Критерии готовности Этапа 1

- [ ] **API-сервер запущен** на `http://localhost:8080`
- [ ] **Endpoint `/chat`** работает (POST → ответ)
- [ ] **WebSocket `/stream`** работает (стриминг токенами)
- [ ] **Endpoint `/discourse`** работает (консилиум до DONE)
- [ ] **Локальная модель** подключена (TabbyAPI/Ollama)
- [ ] **Служба Windows** установлена (автозапуск)
- [ ] **Промты Директора** исправлены (консенсус достигается)
- [ ] **Кэширование** работает (повторные запросы мгновенные)
- [ ] **Документация API** доступна (Swagger UI на `/docs`)

---

## Скрипты для автоматизации

### `scripts/run-api-server.ps1`
```powershell
# Запуск API-сервера (разработка)
cd D:\GitHub\agent-1
.\.venv\Scripts\Activate.ps1
python api_server.py --reload
```

### `scripts/install-service.ps1`
```powershell
# Установка как служба Windows
$serviceName = "HermesAPI"
$pythonPath = "D:\GitHub\agent-1\.venv\Scripts\python.exe"
$scriptPath = "D:\GitHub\agent-1\api_server.py"
$workDir = "D:\GitHub\agent-1"

nssm install $serviceName $pythonPath $scriptPath
nssm set $serviceName AppDirectory $workDir
nssm set $serviceName AppEnvironmentExtra "PATH=$env:PATH;$workDir\.venv\Scripts"
nssm start $serviceName

Write-Host "Служба $serviceName установлена и запущена"
```

### `scripts/test-api.ps1`
```powershell
# Тестирование API
$baseUrl = "http://localhost:8080"

# Health check
Write-Host "=== Health Check ==="
Invoke-RestMethod -Uri "$baseUrl/health" -Method Get

# Chat test
Write-Host "`n=== Chat Test ==="
$response = Invoke-RestMethod -Uri "$baseUrl/chat" -Method Post `
    -ContentType "application/json" `
    -Body '{"message": "Привет! Как дела?"}'
$response.response

# Discourse test
Write-Host "`n=== Discourse Test ==="
$response = Invoke-RestMethod -Uri "$baseUrl/discourse" -Method Post `
    -ContentType "application/json" `
    -Body '{"prompt": "Напиши функцию сортировки", "max_turns": 3}'
$response.response
```

---

## Следующие шаги

1. **Изучить `run_agent.py`** — найти инициализацию `AIAgent`
2. **Изучить `llm_director.py`** — понять текущую реализацию
3. **Создать `api_server.py`** — базовый скелет (1 endpoint `/chat`)
4. **Протестировать** — `curl http://localhost:8080/chat`

---

*Этот план — живая документация. Обновляй по мере прохождения задач.*
