# Настройки подключения к Hermes API Server

## ⚡ Быстрая настройка Kilo Code (VS Code)

**1. Установи расширение Kilo Code:**
   - Открой VS Code
   - `Ctrl+Shift+X` → Extensions
   - Найди `Kilo Code` → Install

**2. Настрой подключение:**
   - Открой настройки Kilo Code (значок шестерёнки)
   - Заполни:

| Поле | Значение |
|------|----------|
| **API Provider** | `OpenAI Compatible` |
| **API Endpoint** | `http://localhost:8765` |
| **API Key** | `hermes-secret-key-2026` |
| **Model ID** | `Hermes` |

**3. Проверь:**
   - Открой чат Kilo Code (`Ctrl+Shift+P` → Kilo Code: Show Chat)
   - Напиши: `Привет! Тест.`
   - Должен прийти ответ от Hermes Agent

**Важно:**
- API сервер должен быть запущен (`python api_server.py`)
- Модель называется `Hermes` (внутри может быть любая — qwen3.5-plus, claude, etc.)
- Стриминг включён автоматически

---

## ⚡ Быстрая настройка Continue (VS Code)

**1. Установи расширение Continue:**
   - VS Code → Extensions → `Continue` → Install

**2. Открой конфиг:**
   - `Ctrl+Shift+P` → `Continue: Open Config`

**3. Добавь модель:**
```json
{
  "models": [
    {
      "title": "Hermes (Local)",
      "provider": "openai",
      "model": "Hermes",
      "apiBase": "http://localhost:8765",
      "apiKey": "hermes-secret-key-2026"
    }
  ]
}
```

---

## Сервер

```
Адрес: http://localhost:8765
Swagger UI: http://localhost:8765/docs
WebSocket: ws://localhost:8765/stream
API Key: hermes-secret-key-2026
```

## Endpoints

### 1. Проверка статуса (GET)

```
GET http://localhost:8765/health
```

**Ответ:**
```json
{
  "status": "ok",
  "provider": "alibaba",
  "model": "qwen3.5-plus"
}
```

---

### 2. Чат (POST)

```
POST http://localhost:8765/chat
Content-Type: application/json

{
  "message": "Привет! Как дела?",
  "session_id": "my-session"  // опционально
}
```

**Ответ:**
```json
{
  "response": "Привет! Дела отлично...",
  "session_id": "my-session"
}
```

---

### 3. Список инструментов (GET)

```
GET http://localhost:8765/tools
```

**Ответ:**
```json
{
  "tools": ["terminal", "read_file", "write_file", ...],
  "toolsets": ["hermes-cli", "web", "file", ...]
}
```

---

### 4. Выполнение инструмента (POST)

```
POST http://localhost:8765/tools/execute
Content-Type: application/json

{
  "tool_name": "terminal",
  "args": {"command": "dir"}
}
```

**Ответ:**
```json
{
  "result": {...}
}
```

---

### 5. WebSocket стриминг

```
ws://localhost:8765/stream
```

**Отправка:**
```json
{"text": "Привет!", "session_id": "my-session"}
```

**Получение (токены):**
```json
{"type": "token", "content": "Пр"}
{"type": "token", "content": "ив"}
{"type": "token", "content": "ет!"}
{"type": "complete", "content": "Привет! Как дела?"}
```

---

## Примеры кода

### Python (requests)

```python
import requests

response = requests.post(
    "http://localhost:8765/chat",
    json={"message": "Привет!"}
)

print(response.json()["response"])
```

### Python (aiohttp + WebSocket)

```python
import aiohttp
import asyncio

async def chat():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect("ws://localhost:8765/stream") as ws:
            await ws.send_json({"text": "Привет!"})
            
            async for msg in ws:
                data = msg.json()
                if data["type"] == "token":
                    print(data["content"], end="", flush=True)
                elif data["type"] == "complete":
                    print("\nГотово!")
                    break

asyncio.run(chat())
```

### JavaScript (fetch)

```javascript
const response = await fetch("http://localhost:8765/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: "Привет!"})
});

const data = await response.json();
console.log(data.response);
```

### JavaScript (WebSocket)

```javascript
const ws = new WebSocket("ws://localhost:8765/stream");

ws.onopen = () => {
    ws.send(JSON.stringify({text: "Привет!"}));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "token") {
        console.log(data.content);
    }
};
```

### curl

```bash
curl -X POST http://localhost:8765/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"Привет!"}'
```

### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8765/chat" -Method POST -ContentType "application/json" -Body '{"message":"Привет!"}'
```

---

## Конфигурация сервера

Файл: `api_server.py`

```python
class Config:
    HOST = "0.0.0.0"      # Слушать все интерфейсы
    PORT = 8765           # Порт
    
    PROVIDER = "alibaba"  # Провайдер модели
    MODEL = "qwen3.5-plus"  # Модель
    
    ENABLED_TOOLSETS = ["hermes-cli"]  # Инструменты
```

---

## Переменные окружения

Сервер читает из `.env` или среды:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DASHSCOPE_API_KEY` | Ключ Alibaba (Qwen) | `sk-d2e...37ea` |
| `OPENROUTER_API_KEY` | Ключ OpenRouter | `sk-pro...zwgA` |
| `HERMES_PROVIDER` | Провайдер по умолчанию | `alibaba` |
| `HERMES_MODEL` | Модель по умолчанию | `qwen3.5-plus` |

---

## Запуск сервера

```powershell
# Активировать venv
.\.venv\Scripts\Activate.ps1

# Запустить
python api_server.py
```

**Ожидай:**
```
============================================================
  Hermes API Server
  http://localhost:8765
  Swagger UI: http://localhost:8765/docs
============================================================
INFO: Uvicorn running on http://0.0.0.0:8765
```

---

## Остановка сервера

- **В терминале:** `Ctrl+C`
- **Если служба Windows:** `nssm stop HermesAPI`
