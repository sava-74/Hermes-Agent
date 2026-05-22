# Настройка API Key для Hermes API Server

## ⚠️ Важно!

Начиная с версии 0.2.0, Hermes API Server требует **API Key** для доступа к endpoints.

Это защищает от несанкционированного доступа — теперь никто не сможет использовать вашего агента без ключа.

---

## API Key по умолчанию

```
hermes-secret-key-2026
```

---

## Как использовать

### 1. В заголовке Authorization (рекомендуется)

```bash
curl -X POST http://localhost:8765/v1/chat/completions \
     -H "Authorization: Bearer hermes-secret-key-2026" \
     -H "Content-Type: application/json" \
     -d '{"model": "qwen3.5-plus", "messages": [{"role": "user", "content": "Привет!"}]}'
```

### 2. В VS Code расширениях

**Continue:**
- API URL: `http://localhost:8765/v1`
- API Key: `hermes-secret-key-2026`

**Kilo Code:**
- Endpoint: `http://localhost:8765/v1`
- API Key: `hermes-secret-key-2026`

**Cline:**
- Custom API: `http://localhost:8765/v1/chat/completions`
- API Key: `hermes-secret-key-2026`

### 3. В Python коде

```python
import requests

response = requests.post(
    "http://localhost:8765/v1/chat/completions",
    headers={
        "Authorization": "Bearer hermes-secret-key-2026"
    },
    json={
        "model": "qwen3.5-plus",
        "messages": [{"role": "user", "content": "Привет!"}]
    }
)
```

---

## Как сменить API Key

### Вариант 1: Через переменную окружения

```powershell
# Windows PowerShell
$env:HERMES_SERVER_API_KEY="мой-супер-секретный-ключ-123"
python api_server.py
```

### Вариант 2: Через .env файл

Создай файл `.env` в папке с `api_server.py`:

```bash
HERMES_SERVER_API_KEY=мой-супер-секретный-ключ-123
```

---

## Обновление клиентов

Если сменили API Key, обновите все клиенты:

1. **Agent проект** (`D:\GitHub\agent`):
   - `core/api_connector.py` → `API_SERVER_KEY = "новый-ключ"`
   - `main.py` → заголовок `Authorization: Bearer новый-ключ`

2. **VS Code расширения**:
   - Настройки расширения → API Key

3. **Свои скрипты**:
   - Обновите заголовок `Authorization`

---

## Проверка работы

### Без ключа (должен быть 401):

```bash
curl http://localhost:8765/v1/chat/completions
# Ответ: {"detail": "Unauthorized: Invalid API Key"}
```

### С ключом (должен быть 200):

```bash
curl -H "Authorization: Bearer hermes-secret-key-2026" \
     http://localhost:8765/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "qwen3.5-plus", "messages": [{"role": "user", "content": "Тест"}]}'
```

---

## Исключения (не требуют ключа)

Эти endpoints доступны без ключа:

- `GET /health` — проверка статуса
- `GET /docs` — Swagger UI документация
- `GET /openapi.json` — OpenAPI спецификация

---

## Безопасность

⚠️ **Не используйте ключ по умолчанию в продакшене!**

Для продакшена:
1. Сгенерируйте сложный ключ: `openssl rand -hex 32`
2. Установите через переменную окружения
3. Не храните в коде
4. Используйте HTTPS (не HTTP)

---

## Troubleshooting

### Ошибка 401 Unauthorized

**Причина:** Неправильный API Key или отсутствует заголовок.

**Решение:**
```bash
# Проверьте заголовок
curl -H "Authorization: Bearer правильный-ключ" http://localhost:8765/health
```

### Ошибка 403 Forbidden

**Причина:** Ключ правильный, но нет прав доступа.

**Решение:** Проверьте настройки CORS в `api_server.py`.

---

## Контакты

Если что-то не работает — проверьте логи сервера:
```
INFO:     127.0.0.1:12345 - "POST /v1/chat/completions HTTP/1.1" 200 OK
```

Или логи клиента для деталей ошибки.
