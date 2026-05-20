# herLayStart - Запуск Hermes Agent на русском

## 📖 Описание

**herLayStart** - это скрипт для удобного запуска Hermes Agent на русском языке.

Автоматически:
- ✅ Проверяет виртуальное окружение
- ✅ Устанавливает русский язык (HERMES_LANGUAGE=ru)
- ✅ Запускает Hermes Agent CLI

---

## 🚀 Быстрый старт

### Windows (двойной клик)

Просто дважды кликните на файл:
```
herLayStart.bat
```

### Windows (командная строка)

```cmd
cd d:\GitHub\agent-1
herLayStart.bat
```

### Через Python

```cmd
cd d:\GitHub\agent-1
.venv\Scripts\activate
python herLayStart.py
```

---

## 📋 Команды

| Команда | Описание |
|---------|----------|
| `herLayStart.bat` | Запуск Hermes CLI (интерактивный режим) |
| `herLayStart.bat --tui` | Запуск TUI интерфейса (красивый терминал) |
| `herLayStart.bat --no-tui` | Простой режим (без анимаций) |
| `herLayStart.bat --gateway` | Запуск шлюза для мессенджеров |
| `herLayStart.bat --help` | Показать справку |

---

## 🔧 Требования

1. **Python 3.12+** - уже установлен в `.venv`
2. **Виртуальное окружение** - создаётся при установке Hermes

### Если виртуальное окружение не найдено:

```cmd
cd d:\GitHub\agent-1
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[all]"
```

После этого `herLayStart.bat` заработает.

---

## 🌐 Языковые настройки

Скрипт автоматически устанавливает:
- `HERMES_LANGUAGE=ru` - русский язык интерфейса

### Сменить язык на английский:

Откройте `herLayStart.bat` и измените строку:
```batch
set HERMES_LANGUAGE=en
```

---

## 📁 Структура файлов

```
d:\GitHub\agent-1\
├── herLayStart.py       # Python скрипт (основной)
├── herLayStart.bat      # Batch файл для Windows
├── hermes_cli/
│   └── translations/
│       ├── __init__.py  # Загрузчик переводов
│       └── ru.py        # Русский язык
└── README.ru.md         # Документация на русском
```

---

## 🛠️ Настройки

### Изменить рабочую директорию

По умолчанию используется директория скрипта.

### Добавить свои переводы

Откройте `hermes_cli/translations/ru.py` и добавьте:

```python
MY_MESSAGES = {
    "greeting": "Привет, Hermes!",
    "farewell": "Пока!",
}
```

---

## ❓ Решение проблем

### Ошибка: "Виртуальное окружение не найдено"

**Решение:** Создайте venv (см. раздел "Требования" выше)

### Ошибка: "Python не найден"

**Решение:** Проверьте, что `.venv\Scripts\python.exe` существует

### Hermes не запускается

**Решение:**
1. Проверьте логи в `~/.hermes/logs/`
2. Запустите с флагом `--help` для проверки
3. Убедитесь, что зависимости установлены

### Переводы не работают

**Решение:**
1. Проверьте, что `HERMES_LANGUAGE=ru` установлен
2. Перезапустите Hermes
3. Проверьте, что файл `hermes_cli/translations/ru.py` существует

---

## 📞 Поддержка

- 📚 [Документация Hermes](https://hermes-agent.nousresearch.com/docs/)
- 💬 [Discord сообщество](https://discord.gg/NousResearch)
- 🐛 [Сообщить об ошибке](https://github.com/NousResearch/hermes-agent/issues)

---

## 📝 Примеры использования

### 1. Обычный запуск

```cmd
herLayStart.bat
```

### 2. Запуск шлюза для Telegram

```cmd
herLayStart.bat --gateway
```

### 3. TUI интерфейс (красивый)

```cmd
herLayStart.bat --tui
```

### 4. Простой режим (если TUI глючит)

```cmd
herLayStart.bat --no-tui
```

---

**Версия:** 1.0  
**Дата:** 20 мая 2026  
**Автор:** Скрипт создан для русскоязычных пользователей Hermes Agent
