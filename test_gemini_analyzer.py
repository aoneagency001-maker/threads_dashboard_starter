#!/usr/bin/env python3
"""
Тест нового Gemini Book Analyzer
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.gemini_book_analyzer import GeminiBookAnalyzer

def main():
    print("\n" + "="*60)
    print("🧪 ТЕСТ GEMINI BOOK ANALYZER")
    print("="*60 + "\n")

    # Находим самую маленькую книгу для теста
    books_dir = Path(__file__).parent / "data" / "books"
    pdf_files = sorted(books_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)

    if not pdf_files:
        print("❌ PDF файлы не найдены")
        return

    # Берем самую маленькую
    test_pdf = pdf_files[0]
    print(f"📖 Тестируем на: {test_pdf.name}")
    print(f"📦 Размер: {test_pdf.stat().st_size / 1024 / 1024:.2f} MB\n")

    try:
        analyzer = GeminiBookAnalyzer()
        result_path = analyzer.analyze_pdf(str(test_pdf))

        print(f"\n✅ УСПЕХ! Результат: {result_path}")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
