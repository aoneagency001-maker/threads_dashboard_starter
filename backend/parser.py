import fitz  # PyMuPDF
import json
import re
from pathlib import Path
import os
from openai import OpenAI
from typing import Optional, List, Dict, Any
from tqdm import tqdm
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# Настройка OpenAI (через переменную окружения)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Гарантируем наличие директорий данных
BASE_DIR = Path(__file__).resolve().parents[1]
BOOKS_DIR = BASE_DIR / "data" / "books"
QUOTES_DIR = BASE_DIR / "data" / "quotes"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
QUOTES_DIR.mkdir(parents=True, exist_ok=True)

def _slugify_filename(file_path: str) -> str:
    name = Path(file_path).stem
    # простая нормализация имени файла
    name = re.sub(r"[^\w\-]+", "-", name, flags=re.IGNORECASE)
    name = re.sub(r"-+", "-", name).strip("-")
    return name.lower() or "book"

def _quotes_output_path_for_book(file_path: str) -> Path:
    slug = _slugify_filename(file_path)
    return QUOTES_DIR / f"{slug}.json"


def _infer_author_and_topic_from_name(name: str) -> Dict[str, str]:
    name_low = name.lower()
    author = ""
    topic = ""
    # Heuristics by filename
    if any(k in name_low for k in ["brunson", "dotcom secrets", "dot com secrets", "traffic secrets", "expert secrets"]):
        author = "russell brunson"
        topic = "маркетинг и продажи воронки"
    elif any(k in name_low for k in ["sales", "продаж", "selling"]):
        topic = "продажи"
    elif any(k in name_low for k in ["marketing", "маркетинг", "ads", "advertis"]):
        topic = "маркетинг"
    return {"author": author, "topic": topic}

def _infer_topic_via_llm(sample_text: str, fallback_topic: str) -> str:
    if client is None:
        return fallback_topic
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Определи главный предмет книги одной-двумя словами (на русском), напр.: продажи, маркетинг, психология, менеджмент."},
                {"role": "user", "content": sample_text[:4000]},
            ],
            temperature=0.0,
        )
        topic = (resp.choices[0].message.content or "").strip().lower()
        # normalize simple outputs
        topic = topic.replace("главная тема:", "").strip()
        return topic or fallback_topic
    except Exception:
        return fallback_topic

def _validate_quote_llm(quote: str, topic: str, author: str) -> bool:
    if not quote.strip():
        return False
    # Quick local checks
    bad_markers = ["scan to download", "www.", "http://", "https://", "оглавление", "содержание", "copyright"]
    if any(m in quote.lower() for m in bad_markers):
        return False
    if client is None:
        # Simple heuristic on length and topic keyword presence when available
        if len(quote) < 60:
            return False
        if topic and not any(t in quote.lower() for t in topic.split()[:2]):
            # allow pass if topic heuristics are too strict
            return True
        return True
    try:
        sys = (
            "Ты валидатор цитат. Ответь строго JSON {valid: boolean}. "
            "Критерии: по теме книги ('" + (topic or "") + "'), без рекламы других книг/авторов, полезно/содержательно, без служебного мусора."
        )
        if author:
            sys += " Автор книги: " + author + "."
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": quote[:6000]},
            ],
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content) if content.strip().startswith("{") else {}
        return bool(data.get("valid") is True)
    except Exception:
        return len(quote) >= 60

def filter_quotes(quotes: List[str]) -> List[str]:
    """Смысловая фильтрация: возвращает только сильные цитаты. Использует GPT, при недоступности — возврат исходных."""
    if not quotes:
        return []
    if client is None:
        return quotes
    batch_size = 100
    selected: List[str] = []
    for i in range(0, len(quotes), batch_size):
        chunk_list = quotes[i : i + batch_size]
        chunk = "\n".join(chunk_list)
        user_prompt = (
            "Найди в этом тексте только ключевые, полезные или вдохновляющие цитаты, "
            "которые можно использовать как советы, инсайты или мотивацию. "
            "Не бери общие описания, служебные части книги или бессмысленные фрагменты. "
            "Верни чистый список цитат, по одной на строку, без пояснений.\n\n" + chunk
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты выделяешь лучшие цитаты из текста."},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            result = response.choices[0].message.content.strip().split("\n")
            selected.extend([r.strip().strip('"') for r in result if len(r.strip()) >= 40])
        except Exception as e:
            print("Ошибка фильтрации:", e)
            selected.extend(chunk_list)
    return selected

# --- Извлечение текста из PDF ---
def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) >= 5 and isinstance(block[4], str):
                text += block[4].strip() + "\n"
    return text

def extract_pages_from_pdf(file_path: str) -> List[str]:
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

# --- Очистка текста ---
def clean_text(text):
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r"\u00a0", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?])\s+", r"\1\n", text)
    return text

# --- Перевод текста ---
def translate_text(text, target_lang="ru"):
    if not text:
        return text
    if client is None:
        return text
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Переведи этот текст на {target_lang}, сохрани стиль и краткость."},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        translated = response.choices[0].message.content.strip()
        return translated
    except Exception as e:
        print("Ошибка перевода:", e)
        return text


def _chunk_paragraphs(text: str, max_sentences: int = 5) -> List[str]:
    # Разбиваем на абзацы, затем группируем по 3–5 предложений
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    for p in paragraphs:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]
        for i in range(0, len(sents), max_sentences):
            chunk = " ".join(sents[i:i+max_sentences])
            if len(chunk) >= 80:
                chunks.append(chunk)
    return chunks

def analyze_chunk(chunk: str, page_number: Optional[int], *, topic: str = "", author: str = "") -> List[Dict[str, Any]]:
    """Просит модель выделить идеи: summary, quote. Возвращает 0..N элементов."""
    results: List[Dict[str, Any]] = []
    if not chunk.strip():
        return results
    if client is None:
        # Фолбэк — берём кусок как оригинал и summary как первые 20 слов
        words = chunk.split()
        summary = " ".join(words[:20]) + ("…" if len(words) > 20 else "")
        results.append({
            "page": page_number,
            "original": chunk,
            "summary": summary,
            "quote": chunk,
        })
        return results

    system_prompt = (
        "Проанализируй текст из книги и верни только идеи/цитаты ПО ТЕМЕ '" + (topic or "") + "'. "
        "Игнорируй всё оффтоп: рекламу других книг, биографии, оглавления, технический мусор. "
        "Если указано, учитывай автора и не включай промо других авторов. "
        "Верни JSON-массив объектов с полями summary и quote (по-русски кратко)."
        + (" Автор: " + author + "." if author else "")
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk[:6000]},
            ],
            temperature=0.2,
            response_format={"type": "json_object"} if hasattr(client, "chat") else None,
        )
        content = response.choices[0].message.content.strip()
        # Пытаемся распарсить как JSON-объект с ключом quotes или массив
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            # Попытка вытащить JSON из текста
            match = re.search(r"\{[\s\S]*\}$", content)
            if match:
                parsed = json.loads(match.group(0))
        if isinstance(parsed, dict) and "quotes" in parsed:
            items = parsed["quotes"]
        elif isinstance(parsed, list):
            items = parsed
        else:
            items = []
        for it in items:
            summary = (it.get("summary") or it.get("idea") or "").strip()
            quote = (it.get("quote") or it.get("text") or "").strip()
            if quote:
                results.append({
                    "page": page_number,
                    "original": chunk,
                    "summary": summary,
                    "quote": quote,
                })
    except Exception as e:
        print("Ошибка анализа куска:", e)
    return results


def extract_insightful_quotes(file_path: str, min_total: int = 20, max_total: int = 50) -> List[Dict[str, Any]]:
    pages = extract_pages_from_pdf(file_path)
    collected: List[Dict[str, Any]] = []
    originals = set()
    # Infer author/topic
    name = Path(file_path).stem
    meta = _infer_author_and_topic_from_name(name)
    # try to refine topic via LLM on first page
    sample_text = clean_text(pages[0]) if pages else ""
    topic = _infer_topic_via_llm(sample_text, meta.get("topic", ""))
    author = meta.get("author", "")
    for idx, page_text in enumerate(pages, start=1):
        cleaned_page = clean_text(page_text)
        for chunk in _chunk_paragraphs(cleaned_page):
            analyzed = analyze_chunk(chunk, page_number=idx, topic=topic, author=author)
            for item in analyzed:
                key = (item.get("quote") or item.get("original"))
                if key and key not in originals:
                    collected.append(item)
                    originals.add(key)
                if len(collected) >= max_total:
                    break
            if len(collected) >= max_total:
                break
        if len(collected) >= max_total:
            break
    # Если мало, доберём из всего текста эвристикой
    if len(collected) < min_total:
        whole = clean_text("\n".join(pages))
        for chunk in _chunk_paragraphs(whole):
            if chunk not in originals:
                collected.append({
                    "page": None,
                    "original": chunk,
                    "summary": "",
                    "quote": chunk,
                })
                originals.add(chunk)
            if len(collected) >= min_total:
                break
    # LLM-based validation: keep only on-topic, meaningful quotes
    validated: List[Dict[str, Any]] = []
    for it in collected:
        q = (it.get("quote") or it.get("original") or "").strip()
        if _validate_quote_llm(q, topic=topic, author=author):
            validated.append(it)
        if len(validated) >= max_total:
            break
    return validated[:max_total]

def save_quotes_file(book_title: str, quotes: List[Dict[str, Any]], output_path: str) -> int:
    payload = {"book": book_title, "quotes": quotes}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(quotes)


# --- Основной процесс ---
from typing import Optional

def process_book(file_path, output_path: Optional[str] = None, force: bool = True) -> str:
    # Путь сохранения: data/quotes/<book>.json
    out_path = output_path or str(_quotes_output_path_for_book(file_path))
    if not force and Path(out_path).exists():
        return out_path

    # Извлекаем лучшие цитаты с номерами страниц
    quotes_raw = extract_insightful_quotes(file_path)
    book_title = Path(file_path).stem
    # Переводим и формируем итоговую структуру
    final: List[Dict[str, Any]] = []
    for item in tqdm(quotes_raw, desc="Translating", unit="q"):
        original = item.get("original", "")
        quote = item.get("quote") or original
        summary = item.get("summary", "")
        page = item.get("page")
        translated_text = translate_text(quote, target_lang="ru")
        final.append({
            "page": page,
            "original": original,
            "summary": summary,
            "quote": quote,
            "translated": translated_text,
        })

    count = save_quotes_file(book_title, final, out_path)
    print(f"✅ Извлечено и переведено {count} цитат. Сохранено в {out_path}")
    return out_path

if __name__ == "__main__":
    default_pdf = str(BOOKS_DIR / "DotCom Secrets PDF.pdf")
    process_book(default_pdf)
