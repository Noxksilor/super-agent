# Super Agent - Autonomous AI Agent for PC Automation

Автономный ИИ-агент для автоматизации задач на вашем ПК.

## Возможности

- **Автономное выполнение задач**: Агент получает задачу текстом и самостоятельно выполняет её до завершения
- **Интеграция с инструментами**:
  - Файловая система (чтение, запись, удаление файлов)
  - Выполнение команд (python, git, docker, n8n и др.)
  - HTTP-запросы и веб-поиск
  - Photoshop автоматизация (ps-agent-mvp)
  - n8n workflows
- **Поддержка LLM**: OpenAI GPT-4, Anthropic Claude, Google Gemini
- **Логирование и отчёты**: Подробные логи и финальные отчёты о выполненных задачах

## Установка

### Быстрая установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd super-agent

# Установка
pip install -e .
```

### Установка с зависимостями для разработки

```bash
pip install -e ".[dev]"
```

## Настройка

### 1. API ключ

Установите переменную окружения для вашего LLM-провайдера:

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Anthropic Claude
export ANTHROPIC_API_KEY="your-api-key"

# Google Gemini
export GOOGLE_API_KEY="your-api-key"
```

### 2. Конфигурационный файл

Создайте конфигурационный файл:

```bash
super-agent config --init
```

Это создаст файл `super_agent_config.json`:

```json
{
  "name": "SuperAgent",
  "max_iterations": 100,
  "log_level": "INFO",
  "log_dir": "./logs",
  "workspace_dir": "./workspace",
  "ps_agent_mvp_path": "C:\\ps_jobs\\job_0001",
  "n8n_endpoint": "http://localhost:5678",
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "tools": {
    "allowed_commands": ["python", "pip", "git", "docker", "n8n", "node", "npm"],
    "allowed_directories": ["C:\\ps_jobs", "C:\\n8n_workflows", "./workspace"],
    "max_command_timeout": 300,
    "web_search_enabled": true,
    "http_requests_enabled": true
  }
}
```

### 3. Проверка статуса

```bash
super-agent status
```

## Использование

### Запуск одной задачи

```bash
# Базовый запуск
super-agent run "Создать Python-скрипт для обработки CSV файлов"

# С указанием провайдера и модели
super-agent run "Настроить n8n workflow" --provider anthropic --model claude-3-sonnet-20240229

# С сохранением отчёта
super-agent run "Запустить ps-agent-mvp пайплайн" --output report.json

# Подробный вывод
super-agent run "Ваша задача" --verbose
```

### Интерактивный режим

```bash
super-agent interactive
```

В интерактивном режиме:
- Введите задачу и нажмите Enter
- Агент выполнит задачу автономно
- Введите `tools` для списка инструментов
- Введите `status` для проверки статуса
- Введите `exit` для выхода

### Примеры задач

#### Photoshop автоматизация

```bash
super-agent run "Запустить ps-agent-mvp с конфигурацией example_job.json и проверить результат"
```

#### n8n workflows

```bash
super-agent run "Проверить статус n8n и вывести список доступных workflows"
```

#### Разработка

```bash
super-agent run "Создать новый Python-проект с виртуальным окружением и файлом requirements.txt"
```

#### Файловые операции

```bash
super-agent run "Прочитать все Python-файлы в директории ./src и создать документацию"
```

## Доступные инструменты

| Инструмент | Описание |
|------------|----------|
| `file_read` | Чтение содержимого файла |
| `file_write` | Запись в файл |
| `file_delete` | Удаление файла или директории |
| `directory_list` | Список файлов в директории |
| `execute_command` | Выполнение shell-команд |
| `http_request` | HTTP-запросы |
| `web_search` | Веб-поиск |
| `ps_agent` | Photoshop автоматизация |
| `n8n` | n8n workflow управление |

## Логирование

Все логи сохраняются в директорию `./logs`:

- `debug_<task_id>.log` - подробные логи выполнения
- `progress_<task_id>.json` - прогресс в JSON формате
- `task_history.json` - история всех задач

## Безопасность

### Ограничения

- **Разрешённые команды**: Только команды из белого списка могут выполняться
- **Разрешённые директории**: Доступ только к указанным директориям
- **Таймаут**: Ограничение времени на выполнение команд

### Важно

- Агент **не** создаёт новые задачи самостоятельно
- Агент работает **только** над задачей, которую вы дали
- Агент **не** трогает проекты вне разрешённых директорий

## Архитектура

```
super_agent/
├── __init__.py          # Пакет
├── __main__.py          # Точка входа
├── agent.py             # Основной класс агента
├── cli.py               # CLI интерфейс
├── config.py            # Конфигурация
├── llm/                 # LLM провайдеры
│   ├── base.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── google_provider.py
└── tools/               # Инструменты
    ├── base.py
    ├── file_tools.py
    ├── command_tool.py
    ├── http_tool.py
    ├── ps_agent_tool.py
    └── n8n_tool.py
```

## Интеграция с ps-agent-mvp

Агент автоматически интегрируется с вашим ps-agent-mvp проектом:

```python
# Пример использования через Python API
from super_agent import Agent
from super_agent.config import load_config

config = load_config()
config.ps_agent_mvp_path = "C:\\ps_jobs\\job_0001"

agent = Agent(config)
result = agent.execute_task(
    "Запустить Photoshop пайплайн с конфигурацией example_job.json"
)

print(agent.get_task_report())
```

## Интеграция с n8n

```python
# Пример работы с n8n
agent = Agent(config)
result = agent.execute_task(
    "Активировать n8n workflow с ID 123 и проверить его статус"
)
```

## Troubleshooting

### Ошибка: No API key configured

Установите переменную окружения с API ключом:
```bash
export OPENAI_API_KEY="your-key"
```

### Ошибка: Command not allowed

Добавьте команду в разрешённые:
```bash
super-agent config --add-command "your-command"
```

### Ошибка: Access denied

Добавьте директорию в разрешённые:
```bash
super-agent config --add-dir "/path/to/directory"
```

## Разработка

### Запуск тестов

```bash
pytest tests/
```

### Форматирование кода

```bash
black super_agent/
```

### Линтинг

```bash
flake8 super_agent/
```

## Лицензия

MIT License

## Контакты

Для вопросов и предложений создайте Issue в репозитории.
