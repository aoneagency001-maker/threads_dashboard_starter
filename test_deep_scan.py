#!/usr/bin/env python3
"""
Тест глубокого сканирования с Gemini (без Streamlit)
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from backend.agent import deep_scan_with_gemini

def main():
    print("\n" + "="*60)
    print("🧪 ТЕСТ ГЛУБОКОГО СКАНИРОВАНИЯ С GEMINI")
    print("="*60 + "\n")

    # Находим PDF файлы
    books_dir = Path(__file__).parent / "data" / "books"
    pdf_files = list(books_dir.glob("*.pdf"))

    if not pdf_files:
        print("❌ PDF файлы не найдены в data/books/")
        return

    print(f"📚 Найдено PDF файлов: {len(pdf_files)}")
    print(f"📖 Используем: {pdf_files[0].name}\n")

    # Запускаем сканирование
    result_path = deep_scan_with_gemini(str(pdf_files[0]))

    if result_path:
        print(f"\n✅ УСПЕХ! Результат сохранен в: {result_path}")

        # Читаем и показываем статистику
        import json
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n📊 СТАТИСТИКА:")
        print(f"   • Всего цитат: {data.get('total_quotes', 0)}")
        print(f"   • Страниц: {data.get('total_pages', 0)}")
        print(f"   • Символов: {data.get('total_chars', 0):,}")

        if data.get('quotes'):
            print(f"\n📝 Первая цитата:")
            first = data['quotes'][0]
            print(f"   {first['quote'][:200]}...")
    else:
        print("\n❌ ОШИБКА: Функция вернула пустой результат")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
