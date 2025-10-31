# Инструкция по публикации на GitHub

## Шаги для публикации кода на GitHub:

1. **Создайте новый репозиторий на GitHub:**
   - Перейдите на https://github.com/new
   - Введите название репозитория (например: `threads_dashboard_starter`)
   - Выберите Public или Private
   - **НЕ добавляйте** README, .gitignore или лицензию (они уже есть в проекте)
   - Нажмите "Create repository"

2. **После создания репозитория, выполните следующие команды:**

```bash
# Добавьте удаленный репозиторий (замените YOUR_USERNAME и YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Переименуйте ветку в main (если нужно)
git branch -M main

# Отправьте код на GitHub
git push -u origin main
```

3. **Альтернативный способ (если хотите использовать SSH):**

```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## Что уже готово:

✅ Git репозиторий инициализирован
✅ Все файлы добавлены в git
✅ Создан .gitignore (исключает .env, __pycache__, большие PDF файлы)
✅ Создан начальный коммит
✅ Добавлен __init__.py для backend пакета

## Важные файлы в репозитории:

- `app.py` - главный файл Streamlit приложения
- `backend/` - модули для обработки книг и цитат
  - `agent.py` - AI агент для улучшения цитат
  - `parser.py` - парсер PDF файлов
  - `smart_quote_extractor.py` - умный экстрактор цитат
- `requirements.txt` - зависимости проекта
- `README.md` - основная документация
- `.gitignore` - исключения для git

## После публикации:

Не забудьте создать файл `.env` в корне проекта с вашими API ключами (см. `env_template.txt`).

