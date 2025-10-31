"""
Улучшенный парсер книг с использованием Claude API и строгой валидацией
"""
import fitz  # PyMuPDF
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from .llm_client import get_llm_client
from .prompts import (
    get_extract_quotes_prompts,
    get_translate_prompts,
    get_infer_topic_prompts
)
from .quote_validator import QuoteValidator

# Гарантируем наличие директорий данных
BASE_DIR = Path(__file__).resolve().parents[1]
BOOKS_DIR = BASE_DIR / "data" / "books"
QUOTES_DIR = BASE_DIR / "data" / "quotes"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
QUOTES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def _slugify_filename(file_path: str) -> str:
    """Нормализует имя файла"""
    name = Path(file_path).stem
    name = re.sub(r"[^\w\-]+", "-", name, flags=re.IGNORECASE)
    name = re.sub(r"-+", "-", name).strip("-")
    return name.lower() or "book"


def _quotes_output_path_for_book(file_path: str) -> Path:
    """Возвращает путь для сохранения цитат"""
    slug = _slugify_filename(file_path)
    return QUOTES_DIR / f"{slug}.json"


def _infer_author_and_topic_from_name(name: str) -> Dict[str, str]:
    """Определяет автора и тему по имени файла (эвристика)"""
    name_low = name.lower()
    author = ""
    topic = ""

    # Известные авторы и книги
    known_books = {
        ("brunson", "dotcom secrets", "dot com secrets", "traffic secrets", "expert secrets"): {
            "author": "Russell Brunson",
            "topic": "маркетинг и воронки продаж"
        },
        ("cialdini", "influence", "влияние"): {
            "author": "Robert Cialdini",
            "topic": "психология влияния"
        },
        ("kotler", "marketing"): {
            "author": "Philip Kotler",
            "topic": "маркетинг"
        },
    }

    for keywords, info in known_books.items():
        if any(k in name_low for k in keywords):
            return info

    # Общие эвристики по темам
    if any(k in name_low for k in ["sales", "продаж", "selling"]):
        topic = "продажи"
    elif any(k in name_low for k in ["marketing", "маркетинг", "ads", "advertis"]):
        topic = "маркетинг"
    elif any(k in name_low for k in ["business", "бизнес", "entrepreneur"]):
        topic = "бизнес и предпринимательство"
    elif any(k in name_low for k in ["psychology", "психолог"]):
        topic = "психология"

    return {"author": author, "topic": topic}


# ============================================
# ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ PDF
# ============================================

def extract_pages_from_pdf(file_path: str) -> List[str]:
    """Извлекает текст постранично из PDF"""
    pages: List[str] = []
    doc = fitz.open(file_path)

    for page in doc:
        blocks = page.get_text("blocks")
        chunks: List[str] = []

        for block in blocks:
            if len(block) >= 5 and isinstance(block[4], str):
                chunks.append(block[4].strip())

        pages.append("\n".join(chunks))

    return pages


def clean_text(text: str) -> str:
    """Очищает текст от артефактов"""
    # Убираем лишние табы и переносы
    text = re.sub(r"[\t\r]+", " ", text)
    # Убираем неразрывные пробелы
    text = re.sub(r"\u00a0", " ", text)
    # Нормализуем пробелы
    text = re.sub(r"\s+", " ", text).strip()
    # Добавляем переносы после знаков препинания для читаемости
    text = re.sub(r"([.!?])\s+", r"\1\n", text)

    return text


# ============================================
# РАБОТА С LLM
# ============================================

def infer_topic_via_llm(sample_text: str, fallback_topic: str) -> str:
    """Определяет тему книги через LLM"""
    llm_client = get_llm_client()

    if not llm_client.is_available():
        return fallback_topic

    system_prompt, user_prompt = get_infer_topic_prompts(sample_text)

    try:
        response = llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_type="fast",  # Быстрая модель для простой задачи
            temperature=0.0,
            response_format="json"
        )

        if response:
            data = llm_client.parse_json_response(response)
            if data and "topic" in data:
                confidence = data.get("confidence", 0.0)
                if confidence >= 0.7:  # Только если уверены
                    return data["topic"].strip().lower()

    except Exception as e:
        print(f"⚠️ Ошибка определения темы через LLM: {e}")

    return fallback_topic


def extract_quotes_from_chunk(
    chunk: str,
    topic: str,
    audience: str = "предпринимателям и маркетологам"
) -> List[Dict[str, Any]]:
    """Извлекает цитаты из текстового фрагмента"""
    llm_client = get_llm_client()

    if not llm_client.is_available():
        # Fallback: возвращаем сам текст как одну цитату
        return [{
            "summary": chunk[:100] + "..." if len(chunk) > 100 else chunk,
            "quote": chunk[:200],
            "category": "general",
            "style": "insight",
            "target_audience": "general",
            "practical_value": 0.5
        }]

    system_prompt, user_prompt = get_extract_quotes_prompts(chunk, topic, audience)

    try:
        response = llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_type="smart",  # Умная модель для качественного извлечения
            temperature=0.3,
            max_tokens=2048,
            response_format="json"
        )

        if not response:
            return []

        data = llm_client.parse_json_response(response)
        if not data or "quotes" not in data:
            return []

        return data["quotes"]

    except Exception as e:
        print(f"⚠️ Ошибка извлечения цитат: {e}")
        return []


def translate_text(text: str, topic: str = "бизнес") -> str:
    """Переводит текст на русский"""
    if not text or not text.strip():
        return text

    llm_client = get_llm_client()

    if not llm_client.is_available():
        return text

    # Быстрая проверка: уже на русском?
    russian_chars = len(re.findall(r'[а-яёА-ЯЁ]', text))
    total_chars = len(re.findall(r'[a-zA-Zа-яёА-ЯЁ]', text))

    if total_chars > 0 and russian_chars / total_chars > 0.5:
        # Уже на русском
        return text

    system_prompt, user_prompt = get_translate_prompts(text, topic)

    try:
        response = llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_type="smart",  # Умная модель для качественного перевода
            temperature=0.2
        )

        if response and response.strip():
            return response.strip()

    except Exception as e:
        print(f"⚠️ Ошибка перевода: {e}")

    return text


# ============================================
# РАЗБИВКА ТЕКСТА НА ПАРАГРАФЫ
# ============================================

def chunk_paragraphs(text: str, max_sentences: int = 5) -> List[str]:
    """Разбивает текст на смысловые фрагменты"""
    # Разбиваем на абзацы
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks: List[str] = []

    for paragraph in paragraphs:
        # Разбиваем абзац на предложения
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]

        # Группируем по max_sentences предложений
        for i in range(0, len(sentences), max_sentences):
            chunk = " ".join(sentences[i:i + max_sentences])
            if len(chunk) >= 80:  # Минимальная длина фрагмента
                chunks.append(chunk)

    return chunks


# ============================================
# ОСНОВНОЙ ПАЙПЛАЙН
# ============================================

def extract_insightful_quotes(
    file_path: str,
    min_total: int = 20,
    max_total: int = 50
) -> List[Dict[str, Any]]:
    """
    Извлекает лучшие цитаты из книги

    Args:
        file_path: Путь к PDF файлу
        min_total: Минимальное количество цитат
        max_total: Максимальное количество цитат

    Returns:
        Список цитат с метаданными
    """
    print(f"\n📚 Обработка книги: {Path(file_path).name}")

    # Извлекаем страницы
    pages = extract_pages_from_pdf(file_path)
    print(f"📄 Извлечено страниц: {len(pages)}")

    # Определяем метаданные книги
    book_name = Path(file_path).stem
    meta = _infer_author_and_topic_from_name(book_name)

    # Уточняем тему через LLM
    sample_text = clean_text(pages[0]) if pages else ""
    topic = infer_topic_via_llm(sample_text, meta.get("topic", "бизнес"))
    author = meta.get("author", "")

    print(f"🎯 Определена тема: {topic}")
    if author:
        print(f"✍️ Автор: {author}")

    # Инициализируем валидатор
    validator = QuoteValidator()

    # Собираем цитаты
    collected: List[Dict[str, Any]] = []
    seen_quotes = set()

    print(f"\n🔍 Извлекаем цитаты...")

    for page_idx, page_text in enumerate(tqdm(pages, desc="Обработка страниц"), start=1):
        if len(collected) >= max_total:
            break

        cleaned_page = clean_text(page_text)

        # Разбиваем на фрагменты
        chunks = chunk_paragraphs(cleaned_page, max_sentences=5)

        for chunk in chunks:
            if len(collected) >= max_total:
                break

            # Извлекаем цитаты из фрагмента
            quotes_from_chunk = extract_quotes_from_chunk(chunk, topic)

            for quote_data in quotes_from_chunk:
                quote_text = quote_data.get("quote", "").strip()

                # Проверяем на дубликаты
                if quote_text in seen_quotes:
                    continue

                # Валидация цитаты
                is_valid, validation_result = validator.validate_quote(quote_text, chunk)

                if is_valid:
                    collected.append({
                        "page": page_idx,
                        "original": chunk,
                        "summary": quote_data.get("summary", ""),
                        "quote": quote_text,
                        "category": quote_data.get("category", "general"),
                        "style": quote_data.get("style", "insight"),
                        "target_audience": quote_data.get("target_audience", "general"),
                        "validation": validation_result
                    })
                    seen_quotes.add(quote_text)

                if len(collected) >= max_total:
                    break

    print(f"\n✅ Извлечено валидных цитат: {len(collected)}")

    # Если мало, снижаем порог валидации (только базовая проверка)
    if len(collected) < min_total:
        print(f"⚠️ Мало цитат ({len(collected)}), снижаем порог валидации...")

        for page_idx, page_text in enumerate(pages, start=1):
            if len(collected) >= min_total:
                break

            cleaned_page = clean_text(page_text)
            chunks = chunk_paragraphs(cleaned_page)

            for chunk in chunks:
                if len(collected) >= min_total:
                    break

                if chunk not in seen_quotes and len(chunk) >= 80:
                    # Только базовая валидация
                    basic_valid, _ = validator._basic_validation(chunk[:200])

                    if basic_valid:
                        collected.append({
                            "page": page_idx,
                            "original": chunk,
                            "summary": "",
                            "quote": chunk[:200],
                            "category": "general",
                            "style": "insight",
                            "target_audience": "general",
                            "validation": {"level": "basic_only"}
                        })
                        seen_quotes.add(chunk[:200])

    return collected[:max_total]


def save_quotes_file(
    book_title: str,
    quotes: List[Dict[str, Any]],
    output_path: str
) -> int:
    """Сохраняет цитаты в JSON файл"""
    payload = {"book": book_title, "quotes": quotes}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return len(quotes)


def process_book(
    file_path: str,
    output_path: Optional[str] = None,
    force: bool = True
) -> str:
    """
    Полная обработка книги: извлечение, перевод, валидация, сохранение

    Args:
        file_path: Путь к PDF файлу
        output_path: Путь для сохранения (опционально)
        force: Перезаписать существующий файл

    Returns:
        Путь к сохранённому файлу
    """
    # Путь сохранения
    out_path = output_path or str(_quotes_output_path_for_book(file_path))

    if not force and Path(out_path).exists():
        print(f"ℹ️ Файл уже существует: {out_path}")
        return out_path

    # Извлекаем цитаты
    quotes_raw = extract_insightful_quotes(file_path)

    if not quotes_raw:
        print("❌ Не удалось извлечь цитаты")
        return ""

    # Переводим цитаты
    book_title = Path(file_path).stem
    book_topic = quotes_raw[0].get("category", "бизнес") if quotes_raw else "бизнес"

    final_quotes: List[Dict[str, Any]] = []

    print(f"\n🌐 Перевод цитат на русский...")

    for item in tqdm(quotes_raw, desc="Перевод", unit="цитата"):
        quote_text = item.get("quote", "")
        translated = translate_text(quote_text, book_topic)

        final_quotes.append({
            "page": item.get("page"),
            "original": item.get("original", ""),
            "summary": item.get("summary", ""),
            "quote": quote_text,
            "translated": translated,
            "engaging": True,
            "category": item.get("category", "general"),
            "style": item.get("style", "insight"),
            "meta": {
                "sentiment": "practical",
                "target_audience": item.get("target_audience", "general"),
                "length": len(quote_text),
                "validation_level": item.get("validation", {}).get("validation_level", "basic")
            }
        })

    # Сохраняем
    count = save_quotes_file(book_title, final_quotes, out_path)

    print(f"\n✅ Готово! Извлечено и сохранено {count} цитат")
    print(f"📁 Файл: {out_path}")

    return out_path


# ============================================
# ТОЧКА ВХОДА
# ============================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = str(BOOKS_DIR / "DotCom Secrets PDF.pdf")

    if Path(pdf_path).exists():
        process_book(pdf_path)
    else:
        print(f"❌ Файл не найден: {pdf_path}")
        print(f"💡 Положите PDF файлы в директорию: {BOOKS_DIR}")
