"""
Утилита для миграции JSON файлов с цитатами в базу данных
"""
import json
from pathlib import Path
from typing import List
from tqdm import tqdm

from .database import get_db, reset_db


def migrate_json_file(json_path: str, db=None) -> int:
    """
    Мигрировать один JSON файл в БД

    Args:
        json_path: Путь к JSON файлу
        db: Инстанс БД (или создаст новый)

    Returns:
        Количество добавленных цитат
    """
    if db is None:
        db = get_db()

    # Загружаем JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    book_title = data.get('book', Path(json_path).stem)
    quotes_list = data.get('quotes', [])

    # Проверяем, есть ли уже эта книга
    existing_book = db.get_book_by_title(book_title)

    if existing_book:
        print(f"📚 Книга '{book_title}' уже существует (ID={existing_book['id']})")
        book_id = existing_book['id']

        # Спрашиваем, что делать
        response = input("   Продолжить добавление цитат? (y/n): ").lower()
        if response != 'y':
            print("   Пропускаем...")
            return 0
    else:
        # Создаём книгу
        book_id = db.add_book(
            title=book_title,
            author="",  # Можно попробовать извлечь из метаданных
            topic="",
            file_path=json_path,
            metadata={"source": "json_migration", "file": str(json_path)}
        )
        print(f"✅ Книга '{book_title}' добавлена (ID={book_id})")

    # Добавляем цитаты
    added_count = 0

    for quote_data in tqdm(quotes_list, desc=f"Миграция {book_title}", unit="цитата"):
        try:
            db.add_quote(book_id, quote_data)
            added_count += 1
        except Exception as e:
            print(f"   ⚠️ Ошибка при добавлении цитаты: {e}")
            continue

    # Обновляем статистику книги
    db.update_book_stats(book_id)

    print(f"✅ Добавлено {added_count} цитат из файла {json_path}")
    return added_count


def migrate_all_json_files(quotes_dir: str = None) -> dict:
    """
    Мигрировать все JSON файлы из директории

    Args:
        quotes_dir: Путь к директории с JSON (по умолчанию data/quotes/)

    Returns:
        Статистика миграции
    """
    if quotes_dir is None:
        base_dir = Path(__file__).resolve().parents[1]
        quotes_dir = base_dir / "data" / "quotes"

    quotes_dir = Path(quotes_dir)

    if not quotes_dir.exists():
        print(f"❌ Директория не найдена: {quotes_dir}")
        return {}

    # Находим все JSON файлы
    json_files = list(quotes_dir.glob("*.json"))

    if not json_files:
        print(f"❌ JSON файлы не найдены в {quotes_dir}")
        return {}

    print(f"\n📁 Найдено {len(json_files)} JSON файлов")
    print("=" * 70)

    # Создаём БД
    db = get_db()

    stats = {
        'total_files': len(json_files),
        'migrated_files': 0,
        'total_quotes': 0,
        'failed_files': []
    }

    for json_file in json_files:
        try:
            print(f"\n📄 Обработка: {json_file.name}")
            added = migrate_json_file(str(json_file), db)
            stats['migrated_files'] += 1
            stats['total_quotes'] += added
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            stats['failed_files'].append(str(json_file))

    print("\n" + "=" * 70)
    print("📊 СТАТИСТИКА МИГРАЦИИ:")
    print(f"   Файлов обработано: {stats['migrated_files']}/{stats['total_files']}")
    print(f"   Всего цитат добавлено: {stats['total_quotes']}")

    if stats['failed_files']:
        print(f"   ⚠️ Ошибки в файлах: {len(stats['failed_files'])}")
        for f in stats['failed_files']:
            print(f"      - {f}")

    # Финальная статистика БД
    db_stats = db.get_stats()
    print(f"\n📚 БАЗА ДАННЫХ:")
    print(f"   Книг: {db_stats['total_books']}")
    print(f"   Цитат: {db_stats['total_quotes']}")
    print(f"   Средний качества: {db_stats['avg_quality']:.2f}")

    if db_stats['by_category']:
        print(f"\n🏷️ ПО КАТЕГОРИЯМ:")
        for cat, count in sorted(db_stats['by_category'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {cat}: {count}")

    return stats


def clear_database(confirm: bool = False):
    """Очистить всю базу данных (ОПАСНО!)"""
    if not confirm:
        response = input("⚠️ ВНИМАНИЕ! Это удалит ВСЕ данные из БД. Продолжить? (yes/no): ")
        if response.lower() != 'yes':
            print("Отменено.")
            return

    db = get_db()

    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM quotes")
    cursor.execute("DELETE FROM books")
    db.conn.commit()

    print("✅ База данных очищена")


# CLI интерфейс
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "migrate":
            # Мигрировать все JSON
            if len(sys.argv) > 2:
                quotes_dir = sys.argv[2]
            else:
                quotes_dir = None

            migrate_all_json_files(quotes_dir)

        elif command == "migrate-one":
            # Мигрировать один файл
            if len(sys.argv) < 3:
                print("Использование: python migrate_json_to_db.py migrate-one <путь_к_файлу.json>")
                sys.exit(1)

            json_path = sys.argv[2]
            migrate_json_file(json_path)

        elif command == "clear":
            # Очистить БД
            clear_database()

        elif command == "stats":
            # Показать статистику
            db = get_db()
            stats = db.get_stats()

            print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ:")
            print(f"   Книг: {stats['total_books']}")
            print(f"   Цитат: {stats['total_quotes']}")
            print(f"   Опубликовано: {stats['published_quotes']}")
            print(f"   Средний качества: {stats['avg_quality']:.2f}")

            if stats['by_category']:
                print(f"\n🏷️ ПО КАТЕГОРИЯМ:")
                for cat, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                    print(f"   {cat}: {count}")

        else:
            print(f"❌ Неизвестная команда: {command}")
            print("\nДоступные команды:")
            print("  migrate              - мигрировать все JSON файлы")
            print("  migrate-one <file>   - мигрировать один JSON файл")
            print("  clear                - очистить базу данных")
            print("  stats                - показать статистику")

    else:
        # Интерактивный режим
        print("🔄 МИГРАЦИЯ JSON → БАЗА ДАННЫХ")
        print("=" * 70)
        print("\nВыберите действие:")
        print("1. Мигрировать все JSON файлы из data/quotes/")
        print("2. Мигрировать один JSON файл")
        print("3. Показать статистику БД")
        print("4. Очистить базу данных")
        print("5. Выход")

        choice = input("\nВаш выбор (1-5): ").strip()

        if choice == "1":
            migrate_all_json_files()

        elif choice == "2":
            json_path = input("Путь к JSON файлу: ").strip()
            if Path(json_path).exists():
                migrate_json_file(json_path)
            else:
                print(f"❌ Файл не найден: {json_path}")

        elif choice == "3":
            db = get_db()
            stats = db.get_stats()
            print("\n📊 СТАТИСТИКА:")
            print(f"   Книг: {stats['total_books']}")
            print(f"   Цитат: {stats['total_quotes']}")
            print(f"   Опубликовано: {stats['published_quotes']}")
            print(f"   Средний качества: {stats['avg_quality']:.2f}")

        elif choice == "4":
            clear_database()

        elif choice == "5":
            print("Выход.")

        else:
            print("❌ Неверный выбор")
