"""
Глубокое извлечение ВСЕХ инсайтов из книги с помощью Google Gemini.

Преимущества Gemini:
- Огромный контекст: до 2M токенов (целая книга за раз!)
- Очень дешево: $0.075 / 1M входных токенов
- Отличное качество для извлечения цитат
"""

import os
import json
from typing import List, Dict, Any
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

class GeminiDeepExtractor:
    """Глубокое извлечение инсайтов из книг с помощью Gemini"""

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Gemini API ключ (если None, берется из .env)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Add GEMINI_API_KEY to .env file")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def extract_all_insights_from_text(self, full_text: str, book_title: str = "") -> List[Dict[str, Any]]:
        """
        Извлекает ВСЕ ценные инсайты из полного текста книги за один запрос.

        Args:
            full_text: Полный текст книги
            book_title: Название книги

        Returns:
            Список всех извлеченных цитат/инсайтов
        """
        print(f"📚 Глубокий анализ книги с Gemini...")
        print(f"📄 Длина текста: {len(full_text)} символов")

        # Промпт для массового извлечения
        system_prompt = """
Ты — эксперт по извлечению ценных инсайтов из бизнес-книг для предпринимателей и маркетологов.

🎯 ТВОЯ ЗАДАЧА: Извлеки ВСЕ ценные мысли, инсайты и практические советы из этой книги.

📊 ЧТО ИЗВЛЕКАТЬ:
1. Ключевые идеи и концепции
2. Практические советы и рекомендации
3. Примеры и кейсы
4. Важные выводы и тезисы
5. Actionable инсайты (что можно внедрить)
6. Цитаты с высокой практической ценностью

❌ ЧТО НЕ ИЗВЛЕКАТЬ:
- Оглавления и заголовки глав
- Технические детали и сноски
- Благодарности и предисловия
- Ссылки на источники
- Повторяющиеся мысли

📏 ТРЕБОВАНИЯ К КАЖДОЙ ЦИТАТЕ:
- Длина: 50-500 символов (для Threads)
- ПОЛНАЯ законченная мысль
- Понятна БЕЗ контекста книги
- Имеет практическую ценность
- Завершается точкой/!/?

🎨 ФОРМАТ ОТВЕТА - строго JSON:
{
  "quotes": [
    {
      "quote": "Текст цитаты (готово для публикации в Threads)",
      "summary": "Краткая суть одним предложением",
      "category": "маркетинг|психология|продажи|мышление|финансы|лидерство",
      "style": "insight|rule|mistake|observation|example|principle",
      "practical_value": 0.0-1.0,
      "engaging_score": 0.0-1.0,
      "page_hint": "примерная страница или раздел"
    },
    ...
  ]
}

💡 СТРАТЕГИЯ:
1. Прочитай ВЕСЬ текст внимательно
2. Найди ВСЕ значимые мысли (не ограничивай себя)
3. Отбери 50-200 лучших цитат (чем больше качественных, тем лучше)
4. Убедись что каждая цитата осмысленная и завершенная
5. Отсортируй по практической ценности

Верни ТОЛЬКО JSON, без дополнительных комментариев.
"""

        user_prompt = f"""
Книга: {book_title if book_title else "Без названия"}

ПОЛНЫЙ ТЕКСТ КНИГИ:
{full_text[:500000]}  # Gemini поддерживает до 2M токенов!

Извлеки ВСЕ ценные инсайты из этой книги в формате JSON.
"""

        try:
            print("🤖 Отправляем запрос Gemini (это может занять 30-60 секунд)...")

            response = self.model.generate_content(
                [system_prompt, user_prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=16384,  # Много токенов для вывода
                )
            )

            # Парсим JSON
            response_text = response.text.strip()

            # Убираем markdown обертку если есть
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            data = json.loads(response_text)
            quotes_list = data.get("quotes", [])

            print(f"✅ Извлечено {len(quotes_list)} цитат!")

            # Добавляем дополнительные поля
            processed_quotes = []
            for idx, quote_data in enumerate(quotes_list, 1):
                processed = {
                    "quote": quote_data.get("quote", "").strip(),
                    "translated": quote_data.get("quote", "").strip(),  # Для совместимости
                    "summary": quote_data.get("summary", ""),
                    "category": quote_data.get("category", "мышление"),
                    "style": quote_data.get("style", "insight"),
                    "engaging": quote_data.get("engaging_score", 0.5) > 0.6,
                    "meta": {
                        "practical_value": quote_data.get("practical_value", 0.7),
                        "engaging_score": quote_data.get("engaging_score", 0.7),
                        "page_hint": quote_data.get("page_hint", ""),
                        "extraction_method": "gemini_deep_scan",
                        "quote_index": idx,
                        "length": len(quote_data.get("quote", ""))
                    }
                }

                # Фильтруем слишком короткие или длинные
                if 30 <= len(processed["quote"]) <= 500:
                    processed_quotes.append(processed)

            print(f"📊 После фильтрации: {len(processed_quotes)} качественных цитат")

            return processed_quotes

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ модели: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"❌ Ошибка при извлечении: {e}")
            return []

    def extract_from_pdf_deep_scan(
        self,
        pdf_path: str,
        output_json_path: str = None
    ) -> str:
        """
        Полное глубокое сканирование PDF книги.

        Args:
            pdf_path: Путь к PDF файлу
            output_json_path: Путь для сохранения результата

        Returns:
            Путь к файлу с результатами
        """
        from . import parser as book_parser

        print(f"\n{'='*60}")
        print(f"🚀 ГЛУБОКОЕ СКАНИРОВАНИЕ КНИГИ С GEMINI")
        print(f"{'='*60}\n")

        # Извлекаем текст из PDF
        print("📖 Шаг 1: Извлечение текста из PDF...")
        pages = book_parser.extract_pages_from_pdf(pdf_path)
        full_text = "\n\n".join([
            book_parser.clean_text(page)
            for page in pages
        ])

        print(f"✅ Извлечено {len(pages)} страниц")
        print(f"📊 Всего символов: {len(full_text):,}")

        # Глубокое извлечение с Gemini
        print(f"\n🔍 Шаг 2: Глубокий анализ с Gemini AI...")
        book_title = Path(pdf_path).stem
        all_quotes = self.extract_all_insights_from_text(full_text, book_title)

        if not all_quotes:
            print("⚠️ Цитаты не извлечены")
            return ""

        # Сохраняем результаты
        print(f"\n💾 Шаг 3: Сохранение результатов...")

        if output_json_path:
            out_path = Path(output_json_path)
        else:
            base_dir = Path(__file__).resolve().parents[1]
            quotes_dir = base_dir / "data" / "quotes"
            quotes_dir.mkdir(parents=True, exist_ok=True)
            out_path = quotes_dir / (book_title.replace(" ", "-") + "_deep.json")

        payload = {
            "book": book_title,
            "extraction_method": "gemini_deep_scan",
            "total_pages": len(pages),
            "total_chars": len(full_text),
            "total_quotes": len(all_quotes),
            "quotes": all_quotes
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"✅ Сохранено в: {out_path}")

        print(f"\n{'='*60}")
        print(f"🎉 ГЛУБОКОЕ СКАНИРОВАНИЕ ЗАВЕРШЕНО!")
        print(f"{'='*60}")
        print(f"📊 Статистика:")
        print(f"   • Страниц обработано: {len(pages)}")
        print(f"   • Извлечено цитат: {len(all_quotes)}")
        print(f"   • Осмысленных: {len([q for q in all_quotes if q.get('engaging')])}")
        print(f"   • Средняя длина: {sum(len(q['quote']) for q in all_quotes) // len(all_quotes)} символов")
        print(f"{'='*60}\n")

        return str(out_path)
