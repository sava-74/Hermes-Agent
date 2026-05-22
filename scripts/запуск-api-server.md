# Запуск Hermes API Server

## Быстрый старт

### 1. Установи зависимости

```powershell
# В терминале VS Code (Ctrl+`)
cd D:\GitHub\agent-1
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] websockets
```

### 2. Настрой API ключ

Создай файл `.env` в корне проекта:

```bash
DASHSCOPE_API_KEY=твой_ключ_alibaba
```

Или установи переменную среды:

```powershell
$env:DASHSCOPE_API_KEY="твой_ключ_alibaba"
```

### 3. Запусти сервер

```powershell
python api_server.py
```

**Ожидай:**
```
============================================================
  Hermes API Server
  http://localhost:8080
  Swagger UI: http://localhost:8080/docs
============================================================
🚀 Запуск Hermes API Server...
   Провайдер: alibaba
   Модель: qwen3.5-plus
   Порт: 8080
✅ Агент инициализирован
```

### 4. Протестируй

**Вариант A: Браузер (Swagger UI)**

Открой: http://localhost:8080/docs

Нажми `POST /chat` → `Try it out` → введи сообщение → `Execute`

**Вариант B: curl**

```powershell
curl -X POST http://localhost:8080/chat ^
     -H "Content-Type: application/json" ^
     -d "{\"message\": \"Привет!\"}"
```

**Вариант C: PowerShell**

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"message": "Привет!"}'
```

---

## Установка как служба Windows

### 1. Установи NSSM

```powershell
winget install nssm
```

### 2. Создай службу

```powershell
# Путь к Python в venv
$pythonPath = "D:\GitHub\agent-1\.venv\Scripts\python.exe"

# Путь к скрипту
$scriptPath = "D:\GitHub\agent-1\api_server.py"

# Рабочая директория
$workDir = "D:\GitHub\agent-1"

# Установить службу
nssm install HermesAPI $pythonPath $scriptPath

# Настроить рабочую директорию
nssm set HermesAPI AppDirectory $workDir

# Настроить переменные окружения
nssm set HermesAPI AppEnvironmentExtra "PATH=$env:PATH;$workDir\.venv\Scripts"
nssm set HermesAPI AppEnvironmentExtra "DASHSCOPE_API_KEY=твой_ключ"

# Запустить службу
nssm start HermesAPI

# Проверить статус
nssm status HermesAPI
```

### 3. Проверь

Открой браузер: http://localhost:8080/health

**Ожидай:**
```json
{"status": "ok", "provider": "alibaba", "model": "qwen3.5-plus"}
```

---

## Остановка службы

```powershell
# Остановить
nssm stop HermesAPI

# Удалить (если нужно)
nssm remove HermesAPI confirm
```

---

## Логи

Служба пишет логи в:

```
%APPDATA%\nssm\HermesAPI\stdout.log
%APPDATA%\nssm\HermesAPI\stderr.log
```

Или смотри в Event Viewer → Windows Logs → Application.

---

## Проблемы и решения

### ❌ "Агент не инициализирован"

**Причина:** API ключ не найден.

**Решение:**
```powershell
$env:DASHSCOPE_API_KEY="твой_ключ"
python api_server.py
```

### ❌ "Port 8080 already in use"

**Причина:** Порт занят другой программой.

**Решение:** Измени порт в `api_server.py`:
```python
PORT = 8081  # или другой
```

### ❌ "ModuleNotFoundError: No module named 'fastapi'"

**Причина:** Зависимости не установлены.

**Решение:**
```powershell
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] websockets
```

---

## Следующий шаг: Chat UI

Когда API-сервер работает, создаём Chat UI:

```powershell
python chat_ui.py
```

(Файл будет создан на Этапе 2)
