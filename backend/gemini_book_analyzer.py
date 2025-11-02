"""
Полный анализ книг с помощью Google Gemini.
Извлекает инсайты по главам, методам и категориям.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import re

load_dotenv()


class GeminiBookAnalyzer:
    """Анализатор книг на основе Gemini AI"""

    # Категории инсайтов
    CATEGORIES = [
        "маркетинг",
        "продажи",
        "психология",
        "мышление",
        "лидерство",
        "финансы",
        "стратегия",
        "продуктивность"
    ]

    # Типы методов
    METHOD_TYPES = [
        "framework",      # Фреймворк/система
        "rule",          # Правило/принцип
        "technique",     # Техника/метод
        "mistake",       # Ошибка/чего избегать
        "case_study",    # Кейс/пример
        "exercise",      # Упражнение
        "insight"        # Инсайт/наблюдение
    ]

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Gemini API ключ (если None, берется из .env)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not found. Add GEMINI_API_KEY to .env file")

        genai.configure(api_key=self.api_key)

        # Используем новую модель с большим контекстом
        # Отключаем фильтры безопасности для обработки любого контента книг
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

    def split_into_chapters(self, full_text: str) -> List[Dict[str, str]]:
        """
        Разбивает текст книги на главы.

        Returns:
            List[Dict]: [{chapter_num, title, content}, ...]
        """
        print("📑 Разбиваем книгу на главы...")

        # Ищем маркеры глав (различные варианты)
        chapter_patterns = [
            r'(?:^|\n)(?:Глава|ГЛАВА|Chapter|CHAPTER)\s+(\d+|[IVX]+)[:\.\s]+([^\n]+)',
            r'(?:^|\n)(\d+)\.\s+([^\n]{10,100})\n',
            r'(?:^|\n)([IVX]+)\.\s+([^\n]{10,100})\n'
        ]

        chapters = []

        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, full_text, re.MULTILINE | re.IGNORECASE))
            if len(matches) >= 3:  # Найдено достаточно глав
                print(f"✓ Найдено {len(matches)} глав по паттерну: {pattern[:30]}...")

                for i, match in enumerate(matches):
                    chapter_num = match.group(1)
                    chapter_title = match.group(2).strip()

                    # Извлекаем текст главы (до следующей главы или до конца)
                    start_pos = match.end()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
                    content = full_text[start_pos:end_pos].strip()

                    if len(content) > 100:  # Только осмысленные главы
                        chapters.append({
                            "chapter_num": chapter_num,
                            "title": chapter_title,
                            "content": content,
                            "length": len(content)
                        })

                if chapters:
                    break

        # Если главы не найдены, делим на равные части
        if not chapters:
            print("⚠️ Явные главы не найдены, делим текст на части по ~50k символов...")
            chunk_size = 50000
            num_chunks = (len(full_text) + chunk_size - 1) // chunk_size

            for i in range(num_chunks):
                start = i * chunk_size
                end = min((i + 1) * chunk_size, len(full_text))
                chapters.append({
                    "chapter_num": str(i + 1),
                    "title": f"Часть {i + 1}",
                    "content": full_text[start:end],
                    "length": end - start
                })

        print(f"✅ Всего глав: {len(chapters)}")
        return chapters

    def extract_insights_from_chapter(
        self,
        chapter_content: str,
        chapter_title: str,
        max_chars: int = 100000
    ) -> List[Dict[str, Any]]:
        """
        Извлекает инсайты из одной главы с помощью Gemini.

        Returns:
            List[Dict]: Список инсайтов с метаданными
        """
        # Обрезаем если слишком длинная
        if len(chapter_content) > max_chars:
            chapter_content = chapter_content[:max_chars]

        prompt = f"""
Проанализируй главу книги и извлеки ВСЕ ценные инсайты.

📖 ГЛАВА: {chapter_title}

🎯 ЗАДАЧА: Найди все ключевые мысли, методы, фреймворки, правила, примеры.

📊 ЧТО ИЗВЛЕКАТЬ:
1. Практические методы и техники
2. Фреймворки и системы
3. Правила и принципы
4. Примеры и кейсы
5. Ошибки и что избегать
6. Ключевые инсайты

❌ ЧТО НЕ ИЗВЛЕКАТЬ:
- Вводные фразы и связки
- Ссылки и сноски
- Технические детали
- Повторы

📏 ФОРМАТ КАЖДОГО ИНСАЙТА:
- Длина: 50-500 символов
- Законченная мысль
- Понятна без контекста
- Практическая ценность

🏷️ КАТЕГОРИИ:
{', '.join(self.CATEGORIES)}

🔧 ТИПЫ МЕТОДОВ:
- framework: фреймворк/система
- rule: правило/принцип
- technique: техника/метод
- mistake: ошибка/чего избегать
- case_study: кейс/пример
- exercise: упражнение
- insight: инсайт/наблюдение

📝 ФОРМАТ ОТВЕТА - строго JSON:
{{
  "insights": [
    {{
      "text": "Текст инсайта (готовый для публикации)",
      "category": "маркетинг|продажи|...",
      "method_type": "framework|rule|technique|...",
      "title": "Краткое название метода/идеи",
      "description": "Подробное описание в 1-2 предложениях",
      "practical_value": 0.0-1.0,
      "actionable": true/false
    }},
    ...
  ]
}}

ТЕКСТ ГЛАВЫ:
{chapter_content[:40000]}

Верни ТОЛЬКО JSON, без дополнительного текста.
"""

        try:
            print(f"   🤖 Анализируем главу '{chapter_title}'...")

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=16384,
                )
            )

            # Парсим ответ
            response_text = response.text.strip()

            # Убираем markdown обертку
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            data = json.loads(response_text)
            insights = data.get("insights", [])

            print(f"   ✅ Извлечено {len(insights)} инсайтов")

            return insights

        except json.JSONDecodeError as e:
            print(f"   ❌ Ошибка парсинга JSON: {e}")
            print(f"   Ответ: {response_text[:300]}...")
            return []
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return []

    def analyze_full_book(
        self,
        full_text: str,
        book_title: str
    ) -> Dict[str, Any]:
        """
        Полный анализ книги: разбивка на главы + извлечение инсайтов.

        Returns:
            Dict с полной структурой книги и всеми инсайтами
        """
        print(f"\n{'='*60}")
        print(f"📚 АНАЛИЗ КНИГИ: {book_title}")
        print(f"{'='*60}\n")

        # Шаг 1: Разбиваем на главы
        chapters = self.split_into_chapters(full_text)

        # Шаг 2: Извлекаем инсайты из каждой главы
        print(f"\n🔍 Извлечение инсайтов из {len(chapters)} глав...\n")

        all_insights = []
        chapters_data = []

        for idx, chapter in enumerate(chapters, 1):
            print(f"📖 Глава {idx}/{len(chapters)}: {chapter['title']}")

            insights = self.extract_insights_from_chapter(
                chapter['content'],
                chapter['title']
            )

            # Добавляем метаданные главы к каждому инсайту
            for insight in insights:
                insight['chapter_num'] = chapter['chapter_num']
                insight['chapter_title'] = chapter['title']
                insight['length'] = len(insight.get('text', ''))

            chapters_data.append({
                "chapter_num": chapter['chapter_num'],
                "title": chapter['title'],
                "insights_count": len(insights),
                "content_length": chapter['length']
            })

            all_insights.extend(insights)
            print()

        # Шаг 3: Группируем по категориям и методам
        by_category = {}
        by_method = {}

        for insight in all_insights:
            # По категории
            cat = insight.get('category', 'другое')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(insight)

            # По типу метода
            method = insight.get('method_type', 'insight')
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(insight)

        # Формируем итоговую структуру
        result = {
            "book_title": book_title,
            "total_chapters": len(chapters),
            "total_insights": len(all_insights),
            "analysis_method": "gemini_2.5_flash",

            # Все инсайты (хронологически)
            "all_insights": all_insights,

            # Структура по главам
            "chapters": chapters_data,

            # Группировка по категориям
            "by_category": {
                cat: {
                    "count": len(items),
                    "insights": items
                }
                for cat, items in by_category.items()
            },

            # Группировка по методам
            "by_method": {
                method: {
                    "count": len(items),
                    "insights": items
                }
                for method, items in by_method.items()
            },

            # Статистика
            "statistics": {
                "avg_insight_length": sum(i['length'] for i in all_insights) // len(all_insights) if all_insights else 0,
                "actionable_count": len([i for i in all_insights if i.get('actionable')]),
                "high_value_count": len([i for i in all_insights if i.get('practical_value', 0) >= 0.7])
            }
        }

        print(f"\n{'='*60}")
        print(f"✅ АНАЛИЗ ЗАВЕРШЕН!")
        print(f"{'='*60}")
        print(f"📊 Статистика:")
        print(f"   • Глав: {len(chapters)}")
        print(f"   • Всего инсайтов: {len(all_insights)}")
        print(f"   • Практичных: {result['statistics']['actionable_count']}")
        print(f"   • Высокой ценности: {result['statistics']['high_value_count']}")
        print(f"   • Категорий: {len(by_category)}")
        print(f"{'='*60}\n")

        return result

    def analyze_pdf(
        self,
        pdf_path: str,
        output_json_path: Optional[str] = None
    ) -> str:
        """
        Анализирует PDF книгу и сохраняет результат.

        Returns:
            Путь к файлу с результатами
        """
        from . import parser as book_parser

        print(f"📖 Загрузка PDF: {pdf_path}")

        # Извлекаем текст
        pages = book_parser.extract_pages_from_pdf(pdf_path)
        full_text = "\n\n".join([
            book_parser.clean_text(page)
            for page in pages
        ])

        print(f"✅ Извлечено {len(pages)} страниц, {len(full_text):,} символов")

        # Анализируем
        book_title = Path(pdf_path).stem
        result = self.analyze_full_book(full_text, book_title)

        # Сохраняем
        if output_json_path:
            out_path = Path(output_json_path)
        else:
            base_dir = Path(__file__).resolve().parents[1]
            quotes_dir = base_dir / "data" / "quotes"
            quotes_dir.mkdir(parents=True, exist_ok=True)
            out_path = quotes_dir / f"{book_title.replace(' ', '-')}_gemini_analysis.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"💾 Результаты сохранены: {out_path}\n")

        return str(out_path)
