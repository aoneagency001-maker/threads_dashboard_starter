import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import re

from openai import OpenAI
from tqdm import tqdm
from . import parser as book_parser
from .smart_quote_extractor import SmartQuoteExtractor, QuoteQuality
from .quote_validator import QuoteValidator
from .gemini_extractor import GeminiDeepExtractor
from .claude_client import (
    is_claude_available,
    claude_refine_quotes,
    claude_extract_from_chunk,
    claude_analyze_quality
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _load_quotes(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        return list(payload.get("quotes", []))
    if isinstance(payload, list):
        return payload
    return []


def _save_quotes(book: str, quotes: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"book": book, "quotes": quotes}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _refine_batch(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Уточняет/полирует уже сформированные элементы цитат, гарантируя структуру и ограничения.
    Теперь использует многоэтапную валидацию для Threads (до 500 символов).
    Вход: список объектов (как минимум с полем quote). Выход: тот же формат с обновлёнными полями.
    """
    if not quotes:
        return []

    # Инициализируем валидатор
    validator = QuoteValidator(use_ai=False)

    # Локальная очистка и валидация как фолбэк
    def _local_polish(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = (item.get("quote") or item.get("translated") or item.get("original") or "").strip()
        text = re.sub(r"\s+", " ", text).strip()

        # Используем валидатор вместо ручных проверок
        temp_quote_data = {
            **item,
            "quote": text
        }

        validated = validator.get_validated_quote(temp_quote_data)
        if validated is None:
            return None

        # Дополняем метаданные
        meta = dict(validated.get("meta") or {})
        meta["length"] = len(validated["quote"])

        return {
            **validated,
            "engaging": True,  # Если прошла валидацию, считаем engaging
            "category": validated.get("category") or "",
            "style": validated.get("style") or "insight",
            "meta": meta,
        }

    # Используем Claude для полировки (если доступен), иначе fallback на GPT или локальную валидацию
    if is_claude_available():
        try:
            # Используем Claude для полировки
            refined_quotes = claude_refine_quotes(quotes)
            # Применяем локальную валидацию к результатам
            result = []
            for quote in refined_quotes:
                validated = _local_polish(quote)
                if validated and validated.get("quote"):
                    result.append(validated)
            return result if result else [it for it in [_local_polish(it) for it in quotes if (it.get("quote") or it.get("original"))] if it is not None]
        except Exception as e:
            print(f"⚠️ Ошибка Claude при обработке батча, используем fallback: {e}")
            # Fallback на локальную валидацию
            return [it for it in [_local_polish(it) for it in quotes if (it.get("quote") or it.get("original"))] if it is not None]
    
    if client is None:
        return [it for it in [_local_polish(it) for it in quotes if (it.get("quote") or it.get("original"))] if it is not None]

    # Fallback на GPT (если Claude недоступен, но GPT доступен)
    # Готовим батч как JSON для строгого ответа
    system_prompt = (
        "Ты — редактор цитат для Threads (Instagram). Проверь и отполируй цитаты.\n\n"
        "🎯 КРИТИЧЕСКИ ВАЖНО:\n"
        "1. ЗАВЕРШЕННОСТЬ: Каждая цитата должна быть ПОЛНОСТЬЮ ОСМЫСЛЕННОЙ и ЗАВЕРШЁННОЙ мыслью\n"
        "2. ДЛИНА: Максимум 500 символов (лимит Threads), оптимально 100-400\n"
        "3. АВТОНОМНОСТЬ: Понятна без контекста книги\n"
        "4. ЦЕННОСТЬ: Имеет практическую пользу для читателя\n\n"
        "✅ Требования к цитате:\n"
        "- Содержит законченную мысль с началом и концом\n"
        "- Не является фрагментом незавершённого предложения\n"
        "- Завершается точкой, восклицательным или вопросительным знаком\n"
        "- Не содержит ссылок, оглавлений, технических терминов\n"
        "- Имеет минимум 5 осмысленных слов\n\n"
        "📏 Контроль длины:\n"
        "- Если цитата >500 символов: сократи до одного-двух законченных предложений\n"
        "- Сохраняй самую ценную мысль\n"
        "- Не обрывай на середине предложения\n\n"
        "Ответ строго JSON {quotes: [...]} в том же порядке.\n"
        "Поля: original, summary, quote (≤500 chars!), translated, engaging, category, style, meta{sentiment, target_audience, length}."
    )
    user_payload = {"quotes": [
        {
            "original": it.get("original", ""),
            "summary": it.get("summary", ""),
            "quote": (it.get("quote") or it.get("translated") or it.get("original") or ""),
            "translated": it.get("translated", ""),
            "engaging": True,
            "category": it.get("category", ""),
            "style": it.get("style", "insight"),
            "meta": it.get("meta", {}),
            "page": it.get("page"),
        }
        for it in quotes
    ]}
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content) if content.strip().startswith("{") else {}
        items = data.get("quotes", []) if isinstance(data, dict) else []
        refined: List[Dict[str, Any]] = []
        for i, obj in enumerate(items):
            base = dict(quotes[i]) if i < len(quotes) else {}
            merged = _local_polish({**base, **obj})
            if merged and merged.get("quote"):
                refined.append(merged)
        return refined
    except Exception as e:
        print("Ошибка агента при обработке батча:", e)
        return [it for it in [_local_polish(it) for it in quotes] if it is not None]


def refine_quotes(input_json_path: str, output_json_path: Optional[str] = None, batch_size: int = 30) -> str:
    """
    Читает существующий файл цитат, отбрасывает мусор и добавляет поле "engaging"
    к сильным цитатам, переписывая их под вовлеченность. Сохраняет только отфильтрованные
    и улучшенные цитаты. Возвращает путь к сохранённому файлу.
    """
    src = Path(input_json_path)
    if not src.exists():
        raise FileNotFoundError(f"Не найден файл: {src}")

    with open(src, "r", encoding="utf-8") as f:
        payload = json.load(f)

    book = payload.get("book") if isinstance(payload, dict) else src.stem
    quotes = _load_quotes(payload)
    if not quotes:
        # ничего не делаем — сохраняем пустой
        out = Path(output_json_path) if output_json_path else src
        _save_quotes(str(book or ""), [], out)
        return str(out)

    refined_all: List[Dict[str, Any]] = []
    for i in tqdm(range(0, len(quotes), batch_size), desc="Refining", unit="batch"):
        batch = quotes[i : i + batch_size]
        refined = _refine_batch(batch)
        # Сохраняем только engaging=true
        refined_all.extend([it for it in refined if it.get("engaging") is True])

    # дедуп по тексту цитаты
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for it in refined_all:
        key = (it.get("quote") or "").strip()
        if key and key not in seen:
            deduped.append(it)
            seen.add(key)

    out = Path(output_json_path) if output_json_path else src
    _save_quotes(str(book or ""), deduped, out)
    return str(out)


def _extract_engaging_from_chunk(chunk: str) -> List[Dict[str, Any]]:
    """Возвращает 1–2 структурированные цитаты из куска текста по новому шаблону."""
    if not chunk.strip():
        return []

    # Фолбэк: эвристика с глаголами и маркетинговыми терминами
    def heuristic_candidates(text: str) -> List[Dict[str, Any]]:
        terms = [
            "воронк", "конвер", "продаж", "лид", "трафик", "аудитори", "вниман", "оффер",
            "маркет", "запуск", "продукт", "вирус", "доход", "клиент", "ценност", "обещан",
        ]
        sents = re.split(r"(?<=[.!?])\s+", text)
        results: List[Dict[str, Any]] = []
        for s in sents:
            sent = s.strip()
            if len(sent) < 60:
                continue
            low = sent.lower()
            if not any(t in low for t in terms):
                continue
            if re.search(r"\b(есть|делай|нужно|должен|можно|стро(й|ить)|понимай|тестируй|запускай)\b", low):
                quote = sent[:250].strip()
                results.append({
                    "original": text,
                    "summary": "",
                    "quote": quote,
                    "translated": quote,
                    "engaging": True,
                    "category": "marketing",
                    "style": "insight",
                    "meta": {"sentiment": "motivational", "target_audience": "entrepreneurs, marketers", "length": len(quote)},
                })
            if len(results) >= 2:
                break
        return results

    # Используем Claude для извлечения (если доступен)
    if is_claude_available():
        try:
            quotes = claude_extract_from_chunk(chunk)
            if quotes:
                # Используем валидатор для проверки каждой цитаты
                validator = QuoteValidator(use_ai=False)
                cleaned: List[Dict[str, Any]] = []
                
                for obj in quotes:
                    q = (obj.get("quote") or "").strip()
                    if not q:
                        continue
                    
                    quote_data = {
                        "original": obj.get("original") or chunk,
                        "summary": obj.get("summary", ""),
                        "quote": q,
                        "translated": obj.get("translated") or q,
                        "engaging": True,
                        "category": obj.get("category", ""),
                        "style": obj.get("style", "insight"),
                        "meta": obj.get("meta") or {},
                    }
                    
                    validated = validator.get_validated_quote(quote_data)
                    if validated:
                        cleaned.append(validated)
                
                return cleaned[:2]
        except Exception as e:
            print(f"⚠️ Ошибка Claude при извлечении, используем fallback: {e}")
            # Fallback на эвристику или GPT
    
    if client is None:
        return heuristic_candidates(chunk)

    # Fallback на GPT (если Claude недоступен)
    system_prompt = (
        "Ты — интеллектуальный редактор цитат для Threads.\n\n"
        "🎯 ЗАДАЧА: Извлеки 1-2 ключевые идеи из текста для предпринимателей и маркетологов.\n\n"
        "🔥 КРИТИЧЕСКИ ВАЖНО - МНОГОЭТАПНАЯ ПРОВЕРКА:\n\n"
        "ЭТАП 1 - ЗАВЕРШЕННОСТЬ:\n"
        "- Цитата содержит ПОЛНУЮ законченную мысль\n"
        "- Понятна БЕЗ контекста книги\n"
        "- Имеет начало и логичный конец\n"
        "- НЕ является обрывком предложения\n"
        "- Заканчивается точкой/!/?\n\n"
        "ЭТАП 2 - ДЛИНА ДЛЯ THREADS:\n"
        "- Максимум: 500 символов (жесткий лимит Threads)\n"
        "- Оптимально: 100-400 символов\n"
        "- Если длиннее: оставь 1-2 самых ценных предложения\n"
        "- НЕ обрывай на середине мысли\n\n"
        "ЭТАП 3 - ОСМЫСЛЕННОСТЬ:\n"
        "- Минимум 5 значимых слов\n"
        "- Практическая ценность для читателя\n"
        "- Вызывает эмоцию или узнавание\n"
        "- Можно добавить эмодзи для вовлечения 🔥⚡️💡\n\n"
        "ЭТАП 4 - ФИНАЛЬНАЯ ПРОВЕРКА:\n"
        "- Нет ссылок, оглавлений, технических терминов\n"
        "- Нет благодарностей, упоминаний авторов\n"
        "- Нет незавершенных списков\n\n"
        "📊 JSON формат {quotes: [...]}, поля:\n"
        "- original: исходный фрагмент\n"
        "- summary: суть в 1 предложении\n"
        "- quote: готовая цитата (≤500 символов!)\n"
        "- translated: перевод\n"
        "- engaging: true\n"
        "- category: маркетинг/психология/продажи/мышление\n"
        "- style: insight/rule/mistake/observation\n"
        "- meta: {sentiment, target_audience, length}\n\n"
        "Ответ строго JSON с ключом quotes."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk[:6000]},
            ],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content) if content.strip().startswith("{") else {}
        arr = data.get("quotes", []) if isinstance(data, dict) else []

        # Используем валидатор для проверки каждой цитаты
        validator = QuoteValidator(use_ai=False)
        cleaned: List[Dict[str, Any]] = []

        for obj in arr:
            q = (obj.get("quote") or "").strip()
            if not q:
                continue

            # Формируем данные цитаты для валидации
            quote_data = {
                "original": obj.get("original") or chunk,
                "summary": obj.get("summary", ""),
                "quote": q,
                "translated": obj.get("translated") or q,
                "engaging": True,
                "category": obj.get("category", ""),
                "style": obj.get("style", "insight"),
                "meta": obj.get("meta") or {},
            }

            # Валидируем через многоэтапный валидатор
            validated = validator.get_validated_quote(quote_data)
            if validated:
                cleaned.append(validated)

        return cleaned[:2]
    except Exception as e:
        print("Ошибка извлечения цитат из куска:", e)
        return heuristic_candidates(chunk)


def harvest_all_from_pdf(pdf_path: str, output_json_path: Optional[str] = None, max_sentences_per_chunk: int = 5) -> str:
    """
    Полный проход по книге: извлекает ВСЕ интересные цитаты и сохраняет их в JSON.
    Использует умный экстрактор для анализа контекста и качества цитат.
    """
    pages = book_parser.extract_pages_from_pdf(pdf_path)
    
    # Инициализируем умный экстрактор
    smart_extractor = SmartQuoteExtractor()
    
    # Подготавливаем данные для умного экстрактора
    text_chunks = []
    page_numbers = []
    
    for idx, page_text in enumerate(pages, start=1):
        cleaned_page = book_parser.clean_text(page_text)
        # Разбиваем страницу на абзацы для более точного анализа
        paragraphs = re.split(r'\n\s*\n', cleaned_page)
        for paragraph in paragraphs:
            if len(paragraph.strip()) > 100:  # Только содержательные абзацы
                text_chunks.append(paragraph)
                page_numbers.append(idx)
    
    # Используем умный экстрактор
    collected = smart_extractor.extract_smart_quotes(text_chunks, page_numbers)
    
    # Если ничего не нашли — попробуем старый метод как fallback
    if not collected:
        print("Умный экстрактор не нашел цитат, используем fallback метод...")
        for idx, page_text in enumerate(pages, start=1):
            cleaned_page = book_parser.clean_text(page_text)
            for chunk in book_parser._chunk_paragraphs(cleaned_page, max_sentences=max_sentences_per_chunk):
                items = _extract_engaging_from_chunk(chunk)
                for it in items:
                    key = (it.get("quote") or "").strip()
                    if key:
                        collected.append({
                            **it,
                            "page": idx,
                        })

    # сохранение
    book_title = Path(pdf_path).stem
    if output_json_path:
        out = Path(output_json_path)
    else:
        # кладём рядом с обычным json из пайплайна parser
        base_dir = Path(__file__).resolve().parents[1]
        quotes_dir = base_dir / "data" / "quotes"
        quotes_dir.mkdir(parents=True, exist_ok=True)
        out = quotes_dir / (Path(book_title).stem.replace(" ", "-") + ".json")
    _save_quotes(book_title, collected, out)
    return str(out)


def improve_existing_quotes(input_json_path: str, output_json_path: Optional[str] = None) -> str:
    """
    Улучшает существующие цитаты с помощью умного экстрактора.
    Анализирует качество и контекст каждой цитаты.
    """
    src = Path(input_json_path)
    if not src.exists():
        raise FileNotFoundError(f"Не найден файл: {src}")

    with open(src, "r", encoding="utf-8") as f:
        payload = json.load(f)

    book = payload.get("book") if isinstance(payload, dict) else src.stem
    quotes = _load_quotes(payload)
    
    if not quotes:
        out = Path(output_json_path) if output_json_path else src
        _save_quotes(str(book or ""), [], out)
        return str(out)
    
    # Инициализируем умный экстрактор
    smart_extractor = SmartQuoteExtractor()
    improved_quotes = []
    
    print(f"Улучшаем {len(quotes)} цитат...")
    
    for quote_data in tqdm(quotes, desc="Улучшение цитат"):
        original_text = quote_data.get("original", "")
        current_quote = quote_data.get("quote", "")
        page_num = quote_data.get("page")
        
        if not original_text or not current_quote:
            continue
            
        # Анализируем текущую цитату
        analyses = smart_extractor.analyze_paragraph(original_text, page_num)
        
        # Ищем лучшую альтернативу
        best_analysis = None
        for analysis in analyses:
            if analysis.quality in [QuoteQuality.EXCELLENT, QuoteQuality.GOOD] and analysis.confidence > 0.6:
                if not best_analysis or analysis.confidence > best_analysis.confidence:
                    best_analysis = analysis
        
        if best_analysis:
            # Используем улучшенную цитату
            improved_quote = {
                **quote_data,
                "quote": best_analysis.text,
                "translated": best_analysis.text,  # Пока без перевода
                "summary": best_analysis.summary,  # Краткая идея
                "engaging": best_analysis.quality == QuoteQuality.EXCELLENT,
                "category": best_analysis.category,
                "meta": {
                    **quote_data.get("meta", {}),
                    "sentiment": best_analysis.sentiment,
                    "target_audience": best_analysis.target_audience,
                    "length": len(best_analysis.text),
                    "confidence": best_analysis.confidence,
                    "context_score": best_analysis.context_score,
                    "practical_value": best_analysis.practical_value,
                    "completeness": best_analysis.completeness,
                    "quote_type": best_analysis.quote_type.value,
                    "reasoning": best_analysis.reasoning,
                    "improved": True
                }
            }
            improved_quotes.append(improved_quote)
        else:
            # Оставляем оригинальную цитату, но добавляем метаданные
            improved_quote = {
                **quote_data,
                "meta": {
                    **quote_data.get("meta", {}),
                    "improved": False,
                    "reasoning": "Не найдено лучшей альтернативы"
                }
            }
            improved_quotes.append(improved_quote)
    
    # Убираем дубликаты
    unique_quotes = []
    seen_quotes = set()
    
    for quote in improved_quotes:
        quote_text = quote.get("quote", "").strip()
        if quote_text and quote_text not in seen_quotes:
            unique_quotes.append(quote)
            seen_quotes.add(quote_text)
    
    # Сохраняем результат
    out = Path(output_json_path) if output_json_path else src
    _save_quotes(str(book or ""), unique_quotes, out)
    
    print(f"✅ Улучшено {len(unique_quotes)} цитат. Сохранено в {out}")
    return str(out)


def deep_scan_with_gemini(pdf_path: str, output_json_path: Optional[str] = None) -> str:
    """
    🚀 ГЛУБОКОЕ СКАНИРОВАНИЕ книги с помощью Gemini.

    Извлекает ВСЕ ценные инсайты из книги за один проход.
    Использует Gemini 2.5 Flash - очень дешево и быстро!

    Args:
        pdf_path: Путь к PDF книге
        output_json_path: Путь для сохранения (опционально)

    Returns:
        Путь к файлу с результатами
    """
    print(f"\n🔧 deep_scan_with_gemini() запущена")
    print(f"📁 PDF путь: {pdf_path}")
    print(f"💾 Output путь: {output_json_path}")

    try:
        print("🏗️ Создание GeminiDeepExtractor...")
        extractor = GeminiDeepExtractor()
        print("✅ Extractor создан успешно")

        print("🚀 Запуск extract_from_pdf_deep_scan()...")
        result = extractor.extract_from_pdf_deep_scan(pdf_path, output_json_path)
        print(f"✅ Результат: {result}")
        return result
    except Exception as e:
        print(f"❌ Ошибка глубокого сканирования: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return ""


