# Русский язык в Hermes Agent

## Быстрое включение

### Способ 1: Переменная окружения (рекомендуется)

Добавьте в ваш `.env` файл (`~/.hermes/.env` или проектном `.env`):

```bash
HERMES_LANGUAGE=ru
```

Или установите в shell перед запуском:

```bash
export HERMES_LANGUAGE=ru  # Linux/macOS
$env:HERMES_LANGUAGE="ru"  # PowerShell
set HERMES_LANGUAGE=ru     # cmd.exe
```

### Способ 2: Конфигурация (в разработке)

В будущем язык можно будет настроить через `config.yaml`:

```yaml
display:
  language: ru
```

## Что переводится

✅ **Переведено:**
- Команды меню `/help`
- Сообщения статуса (Думаю..., Ожидание..., Завершено)
- Сообщения об ошибках
- Подсказки и вопросы
- Баннер приветствия
- Названия инструментов и навыков
- Категории команд

❌ **Не переводится:**
- Код (названия функций, переменных)
- Вывод инструментов (терминал, файлы, API ответы)
- Логи и отладочная информация
- Сообщения от LLM моделей

## Структура переводов

Файлы переводов находятся в:
```
hermes_cli/translations/
├── __init__.py    # Загрузчик переводов
└── ru.py          # Русский язык
```

## Добавление своих переводов

Если вы нашли непереведённую строку:

1. Откройте `hermes_cli/translations/ru.py`
2. Найдите нужную категорию (BANNER, COMMANDS, STATUS, и т.д.)
3. Добавьте ключ-значение:

```python
COMMANDS = {
    # ... существующие команды ...
    "mycommand": "Моя команда на русском",
}
```

4. В коде используйте функцию `t()`:

```python
from hermes_cli.translations import t

# Простой перевод
print(t("COMMANDS.mycommand", "My command in English"))

# С форматированием
print(t("BANNER.update_available", "Update available", count=5))
```

## Проверка текущего языка

В Python коде:

```python
from hermes_cli.translations import get_language, is_russian

print(get_language())  # 'ru' или 'en'
print(is_russian())    # True или False
```

## Возврат к английскому

```bash
unset HERMES_LANGUAGE  # Linux/macOS
Remove-Item Env:HERMES_LANGUAGE  # PowerShell
set HERMES_LANGUAGE=  # cmd.exe
```

Или установите `HERMES_LANGUAGE=en`.

## Проблемы и решения

**Вопрос:** Переводы не применяются  
**Решение:** Перезапустите Hermes после установки `HERMES_LANGUAGE`

**Вопрос:** Некоторые строки не переведены  
**Решение:** Добавьте их в `hermes_cli/translations/ru.py` или создайте issue

**Вопрос:** Хочу помочь с переводами  
**Решение:** Отправьте PR с улучшениями в `hermes_cli/translations/ru.py`

## Статус перевода

| Компонент | Статус | Процент |
|-----------|--------|---------|
| Команды CLI | ✅ Готово | 100% |
| Баннер | ✅ Готово | 100% |
| Статусы | ✅ Готово | 100% |
| Ошибки | ✅ Готово | 100% |
| README | ✅ Готово | 100% |
| Документы сайта | 🚧 В процессе | ~0% |

---

**Последнее обновление:** 20 мая 2026
