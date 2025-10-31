"""
Модуль для работы с базой данных цитат

Поддерживает:
- SQLite (локальная база)
- PostgreSQL/Supabase (облачная база)
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class QuotesDatabase:
    """Универсальный класс для работы с БД цитат"""

    def __init__(self, db_type: str = "sqlite", connection_string: Optional[str] = None):
        """
        Инициализация базы данных

        Args:
            db_type: Тип БД ("sqlite" или "postgres")
            connection_string: Строка подключения (для postgres) или путь к файлу (для sqlite)
        """
        self.db_type = db_type

        if db_type == "sqlite":
            # SQLite: локальная база данных
            if connection_string:
                self.db_path = connection_string
            else:
                # По умолчанию: data/quotes.db
                base_dir = Path(__file__).resolve().parents[1]
                data_dir = base_dir / "data"
                data_dir.mkdir(exist_ok=True)
                self.db_path = str(data_dir / "quotes.db")

            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Возвращать словари
            self._init_sqlite_schema()
            print(f"✅ SQLite база подключена: {self.db_path}")

        elif db_type == "postgres":
            # PostgreSQL/Supabase
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor

                if not connection_string:
                    connection_string = os.getenv("DATABASE_URL")

                if not connection_string:
                    raise ValueError("Не указана строка подключения к PostgreSQL")

                self.conn = psycopg2.connect(connection_string, cursor_factory=RealDictCursor)
                self._init_postgres_schema()
                print(f"✅ PostgreSQL база подключена")
            except ImportError:
                raise ImportError("Установите psycopg2: pip install psycopg2-binary")
        else:
            raise ValueError(f"Неподдерживаемый тип БД: {db_type}")

    def _init_sqlite_schema(self):
        """Создание таблиц для SQLite"""
        cursor = self.conn.cursor()

        # Таблица книг
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                topic TEXT,
                file_path TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_quotes INTEGER DEFAULT 0,
                metadata TEXT  -- JSON с доп. информацией
            )
        """)

        # Таблица цитат
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                page_number INTEGER,
                original_text TEXT,
                quote_text TEXT NOT NULL,
                translated_text TEXT,
                summary TEXT,

                -- Категоризация
                category TEXT,
                style TEXT,
                target_audience TEXT,

                -- Метрики качества
                is_engaging BOOLEAN DEFAULT 0,
                quality_score REAL,
                completeness REAL,
                clarity REAL,
                practical_value REAL,

                -- Дополнительные поля
                length INTEGER,
                validation_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published BOOLEAN DEFAULT 0,
                published_at TIMESTAMP,

                -- Метаданные в JSON
                metadata TEXT,

                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)

        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_book_id ON quotes(book_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_category ON quotes(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_quality ON quotes(quality_score)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_published ON quotes(published)
        """)

        # Таблица для полнотекстового поиска (FTS5)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS quotes_fts USING fts5(
                quote_text,
                translated_text,
                summary,
                content='quotes',
                content_rowid='id'
            )
        """)

        self.conn.commit()

    def _init_postgres_schema(self):
        """Создание таблиц для PostgreSQL"""
        cursor = self.conn.cursor()

        # Таблица книг
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                topic TEXT,
                file_path TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_quotes INTEGER DEFAULT 0,
                metadata JSONB
            )
        """)

        # Таблица цитат
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                page_number INTEGER,
                original_text TEXT,
                quote_text TEXT NOT NULL,
                translated_text TEXT,
                summary TEXT,

                category TEXT,
                style TEXT,
                target_audience TEXT,

                is_engaging BOOLEAN DEFAULT FALSE,
                quality_score REAL,
                completeness REAL,
                clarity REAL,
                practical_value REAL,

                length INTEGER,
                validation_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published BOOLEAN DEFAULT FALSE,
                published_at TIMESTAMP,

                metadata JSONB
            )
        """)

        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_book_id ON quotes(book_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_category ON quotes(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_quality ON quotes(quality_score)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_metadata ON quotes USING GIN (metadata)
        """)

        # Полнотекстовый поиск для PostgreSQL
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotes_search
            ON quotes USING GIN (to_tsvector('russian', quote_text || ' ' || COALESCE(translated_text, '')))
        """)

        self.conn.commit()

    # ============================================
    # КНИГИ
    # ============================================

    def add_book(self, title: str, author: str = "", topic: str = "",
                 file_path: str = "", metadata: Dict = None) -> int:
        """Добавить книгу в БД"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            cursor.execute("""
                INSERT INTO books (title, author, topic, file_path, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (title, author, topic, file_path, json.dumps(metadata or {})))
            book_id = cursor.lastrowid
        else:  # postgres
            cursor.execute("""
                INSERT INTO books (title, author, topic, file_path, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (title, author, topic, file_path, json.dumps(metadata or {})))
            book_id = cursor.fetchone()['id']

        self.conn.commit()
        return book_id

    def get_book(self, book_id: int) -> Optional[Dict]:
        """Получить книгу по ID"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        else:
            cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_book_by_title(self, title: str) -> Optional[Dict]:
        """Получить книгу по названию"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            cursor.execute("SELECT * FROM books WHERE title = ?", (title,))
        else:
            cursor.execute("SELECT * FROM books WHERE title = %s", (title,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def list_books(self, limit: int = 100) -> List[Dict]:
        """Получить список всех книг"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY processed_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def update_book_stats(self, book_id: int):
        """Обновить статистику книги (количество цитат)"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            cursor.execute("""
                UPDATE books
                SET total_quotes = (SELECT COUNT(*) FROM quotes WHERE book_id = ?)
                WHERE id = ?
            """, (book_id, book_id))
        else:
            cursor.execute("""
                UPDATE books
                SET total_quotes = (SELECT COUNT(*) FROM quotes WHERE book_id = %s)
                WHERE id = %s
            """, (book_id, book_id))

        self.conn.commit()

    # ============================================
    # ЦИТАТЫ
    # ============================================

    def add_quote(self, book_id: int, quote_data: Dict) -> int:
        """Добавить цитату в БД"""
        cursor = self.conn.cursor()

        # Извлекаем данные
        page_number = quote_data.get('page')
        original_text = quote_data.get('original', '')
        quote_text = quote_data.get('quote', '')
        translated_text = quote_data.get('translated', quote_text)
        summary = quote_data.get('summary', '')

        category = quote_data.get('category', 'general')
        style = quote_data.get('style', 'insight')
        target_audience = quote_data.get('target_audience', 'general')

        is_engaging = quote_data.get('engaging', False)
        meta = quote_data.get('meta', {})
        validation = quote_data.get('validation', {})

        quality_score = meta.get('confidence', validation.get('overall_score', 0.5))
        completeness = validation.get('completeness', meta.get('completeness', 0.0))
        clarity = validation.get('clarity', 0.0)
        practical_value = validation.get('practical_value', meta.get('practical_value', 0.0))

        length = len(quote_text)
        validation_level = validation.get('validation_level', 'basic')

        # Объединяем все метаданные
        all_metadata = {**meta, **validation, 'original_data': quote_data}

        if self.db_type == "sqlite":
            cursor.execute("""
                INSERT INTO quotes (
                    book_id, page_number, original_text, quote_text, translated_text, summary,
                    category, style, target_audience,
                    is_engaging, quality_score, completeness, clarity, practical_value,
                    length, validation_level, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book_id, page_number, original_text, quote_text, translated_text, summary,
                category, style, target_audience,
                is_engaging, quality_score, completeness, clarity, practical_value,
                length, validation_level, json.dumps(all_metadata)
            ))
            quote_id = cursor.lastrowid
        else:  # postgres
            cursor.execute("""
                INSERT INTO quotes (
                    book_id, page_number, original_text, quote_text, translated_text, summary,
                    category, style, target_audience,
                    is_engaging, quality_score, completeness, clarity, practical_value,
                    length, validation_level, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                book_id, page_number, original_text, quote_text, translated_text, summary,
                category, style, target_audience,
                is_engaging, quality_score, completeness, clarity, practical_value,
                length, validation_level, json.dumps(all_metadata)
            ))
            quote_id = cursor.fetchone()['id']

        self.conn.commit()
        return quote_id

    def get_quotes(self, book_id: Optional[int] = None,
                   category: Optional[str] = None,
                   min_quality: float = 0.0,
                   only_engaging: bool = False,
                   only_unpublished: bool = False,
                   limit: int = 100,
                   offset: int = 0) -> List[Dict]:
        """
        Получить цитаты с фильтрацией

        Args:
            book_id: ID книги (None = все книги)
            category: Категория цитат
            min_quality: Минимальный score качества
            only_engaging: Только engaging цитаты
            only_unpublished: Только неопубликованные
            limit: Максимум результатов
            offset: Смещение для пагинации
        """
        cursor = self.conn.cursor()

        conditions = []
        params = []

        if book_id:
            conditions.append("book_id = ?")
            params.append(book_id)

        if category:
            conditions.append("category = ?")
            params.append(category)

        if min_quality > 0:
            conditions.append("quality_score >= ?")
            params.append(min_quality)

        if only_engaging:
            conditions.append("is_engaging = 1")

        if only_unpublished:
            conditions.append("published = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM quotes
            WHERE {where_clause}
            ORDER BY quality_score DESC, created_at DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        if self.db_type == "postgres":
            query = query.replace("?", "%s")

        cursor.execute(query, params)

        quotes = []
        for row in cursor.fetchall():
            quote_dict = dict(row)
            # Парсим JSON метаданные
            if 'metadata' in quote_dict and quote_dict['metadata']:
                try:
                    quote_dict['metadata'] = json.loads(quote_dict['metadata'])
                except:
                    pass
            quotes.append(quote_dict)

        return quotes

    def search_quotes(self, search_text: str, limit: int = 50) -> List[Dict]:
        """Полнотекстовый поиск по цитатам"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            # FTS5 поиск
            cursor.execute("""
                SELECT quotes.* FROM quotes
                JOIN quotes_fts ON quotes.id = quotes_fts.rowid
                WHERE quotes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (search_text, limit))
        else:  # postgres
            # PostgreSQL full-text search
            cursor.execute("""
                SELECT * FROM quotes
                WHERE to_tsvector('russian', quote_text || ' ' || COALESCE(translated_text, ''))
                      @@ plainto_tsquery('russian', %s)
                ORDER BY quality_score DESC
                LIMIT %s
            """, (search_text, limit))

        return [dict(row) for row in cursor.fetchall()]

    def mark_as_published(self, quote_id: int):
        """Отметить цитату как опубликованную"""
        cursor = self.conn.cursor()

        if self.db_type == "sqlite":
            cursor.execute("""
                UPDATE quotes
                SET published = 1, published_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (quote_id,))
        else:
            cursor.execute("""
                UPDATE quotes
                SET published = TRUE, published_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (quote_id,))

        self.conn.commit()

    def get_stats(self) -> Dict:
        """Получить общую статистику"""
        cursor = self.conn.cursor()

        stats = {}

        # Всего книг
        cursor.execute("SELECT COUNT(*) as count FROM books")
        stats['total_books'] = cursor.fetchone()['count']

        # Всего цитат
        cursor.execute("SELECT COUNT(*) as count FROM quotes")
        stats['total_quotes'] = cursor.fetchone()['count']

        # Опубликованных цитат
        cursor.execute("SELECT COUNT(*) as count FROM quotes WHERE published = ?", (1 if self.db_type == "sqlite" else True,))
        stats['published_quotes'] = cursor.fetchone()['count']

        # Средний качества
        cursor.execute("SELECT AVG(quality_score) as avg FROM quotes")
        stats['avg_quality'] = cursor.fetchone()['avg'] or 0.0

        # По категориям
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM quotes
            GROUP BY category
            ORDER BY count DESC
        """)
        stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}

        return stats

    def close(self):
        """Закрыть соединение"""
        if self.conn:
            self.conn.close()
            print("✅ Соединение с БД закрыто")


# Глобальный инстанс (синглтон)
_global_db: Optional[QuotesDatabase] = None


def get_db(db_type: str = "sqlite", connection_string: Optional[str] = None) -> QuotesDatabase:
    """Получить глобальный инстанс БД"""
    global _global_db

    if _global_db is None:
        _global_db = QuotesDatabase(db_type, connection_string)

    return _global_db


def reset_db():
    """Сбросить глобальный инстанс"""
    global _global_db
    if _global_db:
        _global_db.close()
        _global_db = None


# Тестирование
if __name__ == "__main__":
    # Создаём БД
    db = get_db("sqlite")

    # Добавляем тестовую книгу
    book_id = db.add_book(
        title="DotCom Secrets",
        author="Russell Brunson",
        topic="маркетинг",
        metadata={"pages": 250}
    )
    print(f"✅ Книга добавлена: ID={book_id}")

    # Добавляем тестовую цитату
    quote_id = db.add_quote(book_id, {
        "page": 42,
        "quote": "Лучший продукт не побеждает. Побеждает лучший маркетинг.",
        "translated": "Лучший продукт не побеждает. Побеждает лучший маркетинг.",
        "summary": "Важность маркетинга над качеством продукта",
        "category": "маркетинг",
        "engaging": True,
        "meta": {"confidence": 0.95}
    })
    print(f"✅ Цитата добавлена: ID={quote_id}")

    # Получаем статистику
    stats = db.get_stats()
    print(f"\n📊 Статистика:")
    print(f"   Книг: {stats['total_books']}")
    print(f"   Цитат: {stats['total_quotes']}")
    print(f"   Средний качества: {stats['avg_quality']:.2f}")

    # Получаем цитаты
    quotes = db.get_quotes(book_id=book_id)
    print(f"\n📝 Цитат найдено: {len(quotes)}")
    for q in quotes:
        print(f"   - {q['quote_text'][:60]}...")

    db.close()
