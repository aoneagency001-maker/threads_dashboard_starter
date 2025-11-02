"""
Клиент для работы с Anthropic Claude API.
Используется для написания, редактирования и улучшения текстов цитат.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

load_dotenv()

# Глобальный клиент Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude_client: Optional[Any] = None

if ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY:
    try:
        claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as e:
        print(f"⚠️ Ошибка инициализации Claude: {e}")
        claude_client = None


def get_claude_client():
    """Возвращает клиент Claude или None если не настроен"""
    return claude_client


def is_claude_available() -> bool:
    """Проверяет доступность Claude API"""
    return ANTHROPIC_AVAILABLE and claude_client is not None


def claude_complete(
    system_prompt: str,
    user_message: str,
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4096
) -> Optional[str]:
    """
    Отправляет запрос к Claude API и возвращает ответ.
    
    Args:
        system_prompt: Системный промпт
        user_message: Сообщение пользователя
        model: Модель Claude (по умолчанию claude-3-5-sonnet)
        temperature: Температура (0.0-1.0)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Текст ответа или None если ошибка
    """
    if not is_claude_available():
        return None
    
    try:
        message = claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Claude возвращает список блоков контента
        if message.content:
            # Берем первый блок текста
            if hasattr(message.content[0], 'text'):
                return message.content[0].text
            elif isinstance(message.content[0], str):
                return message.content[0]
        
        return None
    except Exception as e:
        print(f"❌ Ошибка Claude API: {e}")
        return None


def claude_translate(text: str, target_lang: str = "ru") -> str:
    """
    Переводит текст с помощью Claude.
    
    Args:
        text: Текст для перевода
        target_lang: Целевой язык
        
    Returns:
        Переведенный текст
    """
    if not text or not text.strip():
        return text
    
    if not is_claude_available():
        return text
    
    system_prompt = f"Ты профессиональный переводчик. Переведи текст на {target_lang}, сохрани стиль, тон и краткость оригинала."
    
    result = claude_complete(
        system_prompt=system_prompt,
        user_message=text,
        temperature=0.3,
        max_tokens=2048
    )
    
    return result.strip() if result else text


def claude_refine_quotes(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Полирует и улучшает цитаты с помощью Claude.
    
    Args:
        quotes: Список цитат для обработки
        
    Returns:
        Улучшенные цитаты
    """
    if not quotes:
        return []
    
    if not is_claude_available():
        return quotes
    
    system_prompt = """Ты — редактор цитат для Threads (Instagram). Проверь и отполируй цитаты.

🎯 КРИТИЧЕСКИ ВАЖНО:
1. ЗАВЕРШЕННОСТЬ: Каждая цитата должна быть ПОЛНОСТЬЮ ОСМЫСЛЕННОЙ и ЗАВЕРШЁННОЙ мыслью
2. ДЛИНА: Максимум 500 символов (лимит Threads), оптимально 100-400
3. АВТОНОМНОСТЬ: Понятна без контекста книги
4. ЦЕННОСТЬ: Имеет практическую пользу для читателя

✅ Требования к цитате:
- Содержит законченную мысль с началом и концом
- Не является фрагментом незавершённого предложения
- Завершается точкой, восклицательным или вопросительным знаком
- Не содержит ссылок, оглавлений, технических терминов
- Имеет минимум 5 осмысленных слов

📏 Контроль длины:
- Если цитата >500 символов: сократи до одного-двух законченных предложений
- Сохраняй самую ценную мысль
- Не обрывай на середине предложения

Ответ строго JSON {quotes: [...]} в том же порядке.
Поля: original, summary, quote (≤500 chars!), translated, engaging, category, style, meta{sentiment, target_audience, length}."""

    import json
    
    user_payload = {
        "quotes": [
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
        ]
    }
    
    user_message = json.dumps(user_payload, ensure_ascii=False)
    
    response_text = claude_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.2,
        max_tokens=8192
    )
    
    if not response_text:
        return quotes
    
    # Парсим JSON ответ
    try:
        # Убираем markdown обертку если есть
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        refined_quotes = data.get("quotes", []) if isinstance(data, dict) else []
        
        # Объединяем с оригинальными данными
        result = []
        for i, refined in enumerate(refined_quotes):
            if i < len(quotes):
                base = quotes[i]
                merged = {**base, **refined}
                if merged.get("quote"):
                    result.append(merged)
        
        return result if result else quotes
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON от Claude: {e}")
        return quotes


def claude_extract_from_chunk(chunk: str) -> List[Dict[str, Any]]:
    """
    Извлекает 1-2 ключевые идеи из текстового фрагмента с помощью Claude.
    
    Args:
        chunk: Текстовый фрагмент
        
    Returns:
        Список извлеченных цитат
    """
    if not chunk or not chunk.strip():
        return []
    
    if not is_claude_available():
        return []
    
    system_prompt = """Ты — интеллектуальный редактор цитат для Threads.

🎯 ЗАДАЧА: Извлеки 1-2 ключевые идеи из текста для предпринимателей и маркетологов.

🔥 КРИТИЧЕСКИ ВАЖНО - МНОГОЭТАПНАЯ ПРОВЕРКА:

ЭТАП 1 - ЗАВЕРШЕННОСТЬ:
- Цитата содержит ПОЛНУЮ законченную мысль
- Понятна БЕЗ контекста книги
- Имеет начало и логичный конец
- НЕ является обрывком предложения
- Заканчивается точкой/!/?

ЭТАП 2 - ДЛИНА ДЛЯ THREADS:
- Максимум: 500 символов (жесткий лимит Threads)
- Оптимально: 100-400 символов
- Если длиннее: оставь 1-2 самых ценных предложения
- НЕ обрывай на середине мысли

ЭТАП 3 - ОСМЫСЛЕННОСТЬ:
- Минимум 5 значимых слов
- Практическая ценность для читателя
- Вызывает эмоцию или узнавание
- Можно добавить эмодзи для вовлечения 🔥⚡️💡

ЭТАП 4 - ФИНАЛЬНАЯ ПРОВЕРКА:
- Нет ссылок, оглавлений, технических терминов
- Нет благодарностей, упоминаний авторов
- Нет незавершенных списков

📊 JSON формат {quotes: [...]}, поля:
- original: исходный фрагмент
- summary: суть в 1 предложении
- quote: готовая цитата (≤500 символов!)
- translated: перевод
- engaging: true
- category: маркетинг/психология/продажи/мышление
- style: insight/rule/mistake/observation
- meta: {sentiment, target_audience, length}

Ответ строго JSON с ключом quotes."""
    
    user_message = chunk[:6000]  # Ограничиваем длину
    
    response_text = claude_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
        max_tokens=4096
    )
    
    if not response_text:
        return []
    
    # Парсим JSON
    import json
    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        quotes = data.get("quotes", []) if isinstance(data, dict) else []
        return quotes[:2]  # Максимум 2 цитаты
    except json.JSONDecodeError:
        return []


def claude_analyze_quality(quote: str, context: str = "") -> Optional[Dict[str, Any]]:
    """
    Анализирует качество цитаты с помощью Claude.
    
    Args:
        quote: Цитата для анализа
        context: Контекст (опционально)
        
    Returns:
        Словарь с оценками качества или None
    """
    if not quote or not quote.strip():
        return None
    
    if not is_claude_available():
        return None
    
    system_prompt = """Ты эксперт по анализу цитат для социальных сетей. Проанализируй цитату и оцени её качество.

Критерии оценки:
1. ЗАВЕРШЕННОСТЬ - содержит ли цитата законченную мысль?
2. ОСМЫСЛЕННОСТЬ - понятна ли цитата без дополнительного контекста?
3. ПРАКТИЧЕСКАЯ ЦЕННОСТЬ - полезна ли цитата для читателя?
4. ЭМОЦИОНАЛЬНОСТЬ - вызывает ли цитата эмоции или интерес?
5. КОНТЕКСТ - хорошо ли цитата передает суть абзаца?

Верни JSON с полями:
- quality: "excellent"/"good"/"average"/"poor"
- confidence: число от 0 до 1
- context_score: число от 0 до 1
- practical_value: число от 0 до 1  
- completeness: число от 0 до 1
- target_audience: строка
- category: строка
- sentiment: строка
- reasoning: объяснение решения
- quote_type: "full_paragraph"/"half_paragraph"/"specific_quote"/"multiple_sentences"
"""
    
    user_message = f"Цитата: {quote}"
    if context:
        user_message += f"\n\nКонтекст: {context[:1000]}"
    
    response_text = claude_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.2,
        max_tokens=2048
    )
    
    if not response_text:
        return None
    
    # Парсим JSON
    import json
    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        return json.loads(response_text)
    except json.JSONDecodeError:
        return None

