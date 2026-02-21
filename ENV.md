# Формат .env

Переменные окружения для API-ключей задаются в файле `.env` в корне проекта.  
Имена переменных должны совпадать со значением поля `api_id` в таблице `models` (см. DATABASE.md).

## Пример

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...
```

- Не коммитьте `.env` в репозиторий (файл в `.gitignore`).
- Скопируйте `.env.example` в `.env` и подставьте свои ключи.

## Open Router

Через [Open Router](https://openrouter.ai/) можно вызывать много моделей (OpenAI, Anthropic, Google и др.) по одному ключу и одному URL.

- В `.env` задайте переменную, например: `OPENROUTER_API_KEY=sk-or-...`
- В таблице `models` для каждой модели укажите:
  - **api_url**: `https://openrouter.ai/api/v1/chat/completions` (константа `OPENROUTER_API_URL` в `network.py`)
  - **api_id**: `OPENROUTER_API_KEY` (имя переменной в `.env`)
  - **name**: id модели на Open Router, например `openai/gpt-4o`, `anthropic/claude-3-sonnet`, `google/gemini-pro`
- Один и тот же ключ и URL можно использовать для всех записей, меняется только **name** (ид модели).
