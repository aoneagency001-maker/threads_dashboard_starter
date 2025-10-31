# 📊 Руководство по работе с базой данных цитат

## 🎯 Что даёт база данных?

**Преимущества перед JSON:**
- ✅ **Быстрый поиск** - полнотекстовый поиск по всем цитатам
- ✅ **Фильтрация** - по качеству, категориям, книгам
- ✅ **Аналитика** - статистика, топы, тренды
- ✅ **Масштабируемость** - миллионы цитат без проблем
- ✅ **Избежание дубликатов** - проверка перед добавлением
- ✅ **Отслеживание публикаций** - что опубликовано, что нет

## 📁 Структура базы данных

### Таблица `books` (Книги)
```sql
id              - Уникальный ID книги
title           - Название книги
author          - Автор
topic           - Тема (маркетинг, продажи, психология)
file_path       - Путь к PDF файлу
processed_at    - Когда обработана
total_quotes    - Количество цитат
metadata        - JSON с доп. информацией
```

### Таблица `quotes` (Цитаты)
```sql
id                  - Уникальный ID цитаты
book_id             - ID книги (FK)
page_number         - Номер страницы
original_text       - Оригинальный текст (контекст)
quote_text          - Сама цитата
translated_text     - Перевод на русский
summary             - Краткое резюме

category            - Категория (marketing, business, sales)
style               - Стиль (insight, rule, advice)
target_audience     - Целевая аудитория

is_engaging         - Интересная ли цитата
quality_score       - Оценка качества (0-1)
completeness        - Завершённость (0-1)
clarity             - Понятность (0-1)
practical_value     - Практическая ценность (0-1)

length              - Длина цитаты
validation_level    - Уровень валидации
created_at          - Когда добавлена
published           - Опубликована ли
published_at        - Когда опубликована

metadata            - JSON с доп. метаданными
```

## 🚀 Быстрый старт

### 1. Миграция существующих JSON

```bash
# Мигрировать все JSON из data/quotes/
python -m backend.migrate_json_to_db migrate

# Мигрировать один файл
python -m backend.migrate_json_to_db migrate-one data/quotes/your_book.json

# Показать статистику
python -m backend.migrate_json_to_db stats

# Очистить базу
python -m backend.migrate_json_to_db clear
```

### 2. Работа с БД из Python

```python
from backend.database import get_db

# Получить БД (SQLite по умолчанию)
db = get_db()

# ============================================
# КНИГИ
# ============================================

# Добавить книгу
book_id = db.add_book(
    title="DotCom Secrets",
    author="Russell Brunson",
    topic="маркетинг",
    metadata={"pages": 250}
)

# Получить книгу
book = db.get_book(book_id)
print(book['title'])

# Список всех книг
books = db.list_books()
for book in books:
    print(f"{book['title']}: {book['total_quotes']} цитат")

# ============================================
# ЦИТАТЫ
# ============================================

# Добавить цитату
quote_id = db.add_quote(book_id, {
    "page": 42,
    "quote": "Лучший продукт не побеждает. Побеждает лучший маркетинг.",
    "translated": "...",
    "category": "маркетинг",
    "engaging": True,
    "meta": {"confidence": 0.95}
})

# Получить цитаты с фильтрацией
quotes = db.get_quotes(
    book_id=book_id,              # Из конкретной книги
    category="маркетинг",         # Категория
    min_quality=0.8,              # Минимальное качество
    only_engaging=True,           # Только интересные
    only_unpublished=True,        # Только неопубликованные
    limit=10,                     # Максимум результатов
    offset=0                      # Смещение (пагинация)
)

for q in quotes:
    print(f"{q['quote_text']} (качество: {q['quality_score']})")

# Полнотекстовый поиск
results = db.search_quotes("воронка продаж", limit=5)

# Отметить как опубликованную
db.mark_as_published(quote_id)

# ============================================
# СТАТИСТИКА
# ============================================

stats = db.get_stats()
print(f"Книг: {stats['total_books']}")
print(f"Цитат: {stats['total_quotes']}")
print(f"Опубликовано: {stats['published_quotes']}")
print(f"Средний качества: {stats['avg_quality']:.2f}")

# По категориям
for cat, count in stats['by_category'].items():
    print(f"{cat}: {count}")

# Закрыть соединение
db.close()
```

## 📊 Полезные запросы

### Топ-10 лучших цитат
```python
top_quotes = db.get_quotes(
    min_quality=0.9,
    only_engaging=True,
    limit=10
)
```

### Неопубликованные цитаты высокого качества
```python
to_publish = db.get_quotes(
    min_quality=0.8,
    only_unpublished=True,
    limit=5
)
```

### Цитаты из конкретной книги
```python
book = db.get_book_by_title("DotCom Secrets")
quotes = db.get_quotes(book_id=book['id'], limit=100)
```

### Поиск по ключевым словам
```python
marketing_quotes = db.search_quotes("маркетинг воронка", limit=20)
```

## 🔧 Расширенное использование

### Обновить статистику книги
```python
db.update_book_stats(book_id)
```

### Прямые SQL запросы (для экспертов)
```python
cursor = db.conn.cursor()
cursor.execute("""
    SELECT category, AVG(quality_score) as avg_quality
    FROM quotes
    GROUP BY category
    ORDER BY avg_quality DESC
""")
results = cursor.fetchall()
```

## 🌐 PostgreSQL / Supabase (опционально)

Для использования облачной БД:

```python
# Установить psycopg2
pip install psycopg2-binary

# Добавить в .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Использовать PostgreSQL
from backend.database import get_db

db = get_db(
    db_type="postgres",
    connection_string="postgresql://user:pass@host:5432/dbname"
)
```

### Supabase (бесплатный PostgreSQL)

1. Зарегистрируйтесь на https://supabase.com/
2. Создайте проект
3. Получите Connection String
4. Добавьте в `.env`:
   ```
   DATABASE_URL=postgresql://...
   ```

## 📈 Мониторинг и аналитика

```python
from backend.database import get_db

db = get_db()
stats = db.get_stats()

# Качество по категориям
cursor = db.conn.cursor()
cursor.execute("""
    SELECT
        category,
        COUNT(*) as total,
        AVG(quality_score) as avg_quality,
        SUM(CASE WHEN published = 1 THEN 1 ELSE 0 END) as published
    FROM quotes
    GROUP BY category
    ORDER BY avg_quality DESC
""")

for row in cursor.fetchall():
    print(f"{row['category']}: {row['total']} цитат, "
          f"качество {row['avg_quality']:.2f}, "
          f"опубликовано {row['published']}")
```

## 🔄 Интеграция с parser_v2.py

После обработки книги цитаты автоматически сохраняются в БД:

```python
from backend.parser_v2 import process_book

# Обработать книгу и сохранить в БД
output_path = process_book("data/books/your_book.pdf")

# Цитаты теперь доступны через БД
from backend.database import get_db

db = get_db()
book = db.get_book_by_title("your_book")
quotes = db.get_quotes(book_id=book['id'])
```

## 🎯 Best Practices

1. **Всегда закрывайте соединение**
   ```python
   try:
       db = get_db()
       # работа с БД
   finally:
       db.close()
   ```

2. **Используйте транзакции для массовых операций**
   ```python
   cursor = db.conn.cursor()
   try:
       # много операций
       db.conn.commit()
   except:
       db.conn.rollback()
   ```

3. **Регулярно обновляйте статистику**
   ```python
   for book in db.list_books():
       db.update_book_stats(book['id'])
   ```

4. **Делайте backup**
   ```bash
   # SQLite backup
   cp data/quotes.db data/quotes_backup.db
   ```

## 🐛 Устранение проблем

### База данных заблокирована
```python
# Закройте все соединения
from backend.database import reset_db
reset_db()
```

### Потеряны данные
```bash
# Восстановить из JSON
python -m backend.migrate_json_to_db migrate
```

### Ошибка при миграции
```bash
# Очистить и мигрировать заново
python -m backend.migrate_json_to_db clear
python -m backend.migrate_json_to_db migrate
```

## 📚 Дополнительная информация

- **Файл БД:** `data/quotes.db`
- **Размер:** ~1-10 MB на 1000 цитат
- **Производительность:** ~100-1000 операций/сек
- **Лимиты:** миллионы цитат без проблем

---

**Готово! Теперь вы можете эффективно работать с цитатами через базу данных!** 🎉
