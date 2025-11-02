"""
Умный экстрактор цитат с анализом контекста и проверкой качества
"""
import json
import re
from typing import List, Dict, Any, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import os
from openai import OpenAI
from .claude_client import is_claude_available, claude_analyze_quality

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class QuoteType(Enum):
    """Типы цитат по их структуре"""
    FULL_PARAGRAPH = "full_paragraph"  # Весь абзац
    HALF_PARAGRAPH = "half_paragraph"  # Половина абзаца
    SPECIFIC_QUOTE = "specific_quote"   # Конкретная цитата
    MULTIPLE_SENTENCES = "multiple_sentences"  # Несколько предложений


class QuoteQuality(Enum):
    """Уровни качества цитат"""
    EXCELLENT = "excellent"  # Отличная цитата
    GOOD = "good"           # Хорошая цитата
    AVERAGE = "average"     # Средняя цитата
    POOR = "poor"          # Плохая цитата


@dataclass
class QuoteAnalysis:
    """Результат анализа цитаты"""
    text: str
    quote_type: QuoteType
    quality: QuoteQuality
    confidence: float  # 0-1, уверенность в качестве
    context_score: float  # 0-1, насколько хорошо цитата передает контекст
    practical_value: float  # 0-1, практическая ценность
    completeness: float  # 0-1, завершенность мысли
    target_audience: str
    category: str
    sentiment: str
    reasoning: str  # Объяснение решения
    summary: str = ""  # Краткая идея


class SmartQuoteExtractor:
    """Умный экстрактор цитат с анализом контекста"""
    
    def __init__(self):
        self.client = client
        
    def analyze_paragraph(self, paragraph: str, page_num: Optional[int] = None) -> List[QuoteAnalysis]:
        """
        Анализирует абзац и определяет лучший способ извлечения цитат
        
        Args:
            paragraph: Текст абзаца для анализа
            page_num: Номер страницы (опционально)
            
        Returns:
            Список проанализированных цитат с метаданными
        """
        if not paragraph.strip():
            return []
            
        # Очищаем текст
        cleaned_paragraph = self._clean_text(paragraph)
        
        # Определяем структуру абзаца
        structure = self._analyze_paragraph_structure(cleaned_paragraph)
        
        # Извлекаем потенциальные цитаты
        candidates = self._extract_quote_candidates(cleaned_paragraph, structure)
        
        # Анализируем каждую кандидатуру
        analyzed_quotes = []
        for candidate in candidates:
            analysis = self._analyze_quote_quality(candidate, cleaned_paragraph, page_num)
            if analysis.quality != QuoteQuality.POOR:
                analyzed_quotes.append(analysis)
                
        # Сортируем по качеству
        analyzed_quotes.sort(key=lambda x: x.confidence, reverse=True)
        
        return analyzed_quotes[:3]  # Возвращаем топ-3 цитаты
    
    def _clean_text(self, text: str) -> str:
        """Очищает текст от мусора"""
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        # Убираем технические артефакты
        text = re.sub(r'[^\w\s.,!?;:()\-—""''«»]', '', text)
        return text.strip()
    
    def _analyze_paragraph_structure(self, paragraph: str) -> Dict[str, Any]:
        """Анализирует структуру абзаца"""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            'sentence_count': len(sentences),
            'total_length': len(paragraph),
            'avg_sentence_length': sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
            'sentences': sentences,
            'has_questions': any('?' in s for s in sentences),
            'has_commands': any(re.search(r'\b(делай|нужно|должен|можно|следует|важно)\b', s.lower()) for s in sentences),
            'has_examples': any('например' in s.lower() or 'например,' in s.lower() for s in sentences),
        }
    
    def _extract_quote_candidates(self, paragraph: str, structure: Dict[str, Any]) -> List[str]:
        """Извлекает кандидатов на цитаты из абзаца"""
        candidates = []
        sentences = structure['sentences']
        
        # 1. Весь абзац (если не слишком длинный)
        if len(paragraph) <= 400:
            candidates.append(paragraph)
        
        # 2. Половина абзаца
        mid_point = len(sentences) // 2
        if mid_point > 0:
            first_half = ' '.join(sentences[:mid_point])
            second_half = ' '.join(sentences[mid_point:])
            
            if len(first_half) >= 50:
                candidates.append(first_half)
            if len(second_half) >= 50:
                candidates.append(second_half)
        
        # 3. Отдельные предложения (если они содержательные)
        for sentence in sentences:
            if len(sentence) >= 30 and self._is_meaningful_sentence(sentence):
                candidates.append(sentence)
        
        # 4. Группы предложений
        for i in range(len(sentences) - 1):
            group = ' '.join(sentences[i:i+2])
            if len(group) >= 50:
                candidates.append(group)
        
        return list(set(candidates))  # Убираем дубликаты
    
    def _is_meaningful_sentence(self, sentence: str) -> bool:
        """Проверяет, является ли предложение содержательным"""
        # Исключаем служебные фразы
        meaningless_patterns = [
            r'^\d+\.',  # Нумерация
            r'^глава\s+\d+',  # Главы
            r'^страница\s+\d+',  # Страницы
            r'^рисунок\s+\d+',  # Рисунки
            r'^таблица\s+\d+',  # Таблицы
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, sentence.lower()):
                return False
        
        # Проверяем на наличие ключевых слов
        meaningful_indicators = [
            r'\b(продаж|маркетинг|бизнес|клиент|доход|прибыль|воронк|конвер)\b',
            r'\b(важно|нужно|должен|можно|следует|рекомендуется)\b',
            r'\b(результат|эффект|успех|проблема|решение)\b',
        ]
        
        return any(re.search(pattern, sentence.lower()) for pattern in meaningful_indicators)
    
    def _analyze_quote_quality(self, quote: str, full_context: str, page_num: Optional[int]) -> QuoteAnalysis:
        """Анализирует качество цитаты"""
        # Используем Claude для анализа (если доступен)
        if is_claude_available():
            try:
                data = claude_analyze_quality(quote, full_context)
                if data:
                    return QuoteAnalysis(
                        text=quote,
                        quote_type=QuoteType(data.get("quote_type", "specific_quote")),
                        quality=QuoteQuality(data.get("quality", "average")),
                        confidence=float(data.get("confidence", 0.5)),
                        context_score=float(data.get("context_score", 0.5)),
                        practical_value=float(data.get("practical_value", 0.5)),
                        completeness=float(data.get("completeness", 0.5)),
                        target_audience=data.get("target_audience", "general"),
                        category=data.get("category", "general"),
                        sentiment=data.get("sentiment", "neutral"),
                        reasoning=data.get("reasoning", "")
                    )
            except Exception as e:
                print(f"⚠️ Ошибка Claude при анализе качества, используем fallback: {e}")
        
        # Fallback на GPT (если Claude недоступен)
        if self.client is None:
            return self._fallback_analysis(quote, full_context, page_num)
        
        try:
            system_prompt = """
            Ты эксперт по анализу цитат для социальных сетей. Проанализируй цитату и оцени её качество.
            
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
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Цитата: {quote}\n\nКонтекст: {full_context[:1000]}"}
                ],
                temperature=0.2
            )
            
            content = response.choices[0].message.content or "{}"
            data = json.loads(content) if content.strip().startswith("{") else {}
            
            return QuoteAnalysis(
                text=quote,
                quote_type=QuoteType(data.get("quote_type", "specific_quote")),
                quality=QuoteQuality(data.get("quality", "average")),
                confidence=float(data.get("confidence", 0.5)),
                context_score=float(data.get("context_score", 0.5)),
                practical_value=float(data.get("practical_value", 0.5)),
                completeness=float(data.get("completeness", 0.5)),
                target_audience=data.get("target_audience", "general"),
                category=data.get("category", "general"),
                sentiment=data.get("sentiment", "neutral"),
                reasoning=data.get("reasoning", "")
            )
            
        except Exception as e:
            print(f"Ошибка анализа качества цитаты: {e}")
            return self._fallback_analysis(quote, full_context, page_num)
    
    def _fallback_analysis(self, quote: str, full_context: str, page_num: Optional[int]) -> QuoteAnalysis:
        """Резервный анализ без LLM"""
        # Простые эвристики
        length_score = min(len(quote) / 200, 1.0)  # Оптимальная длина ~200 символов
        completeness_score = 1.0 if quote.endswith(('.', '!', '?')) else 0.5
        
        # Расширенная проверка на ключевые слова
        business_words = ['продаж', 'маркетинг', 'бизнес', 'клиент', 'доход', 'прибыль', 'воронк', 'конвер']
        action_words = ['важно', 'нужно', 'должен', 'можно', 'следует', 'рекомендуется', 'делай', 'строи']
        result_words = ['результат', 'эффект', 'успех', 'проблема', 'решение', 'стратегия', 'тактика']
        
        business_score = sum(1 for word in business_words if word in quote.lower()) / len(business_words)
        action_score = sum(1 for word in action_words if word in quote.lower()) / len(action_words)
        result_score = sum(1 for word in result_words if word in quote.lower()) / len(result_words)
        
        meaningful_score = (business_score + action_score + result_score) / 3
        
        # Проверка на практическую ценность
        practical_indicators = [
            'как', 'что', 'почему', 'когда', 'где', 'зачем',  # Вопросы
            'метод', 'способ', 'техника', 'инструмент',  # Методы
            'пример', 'случай', 'история', 'опыт',  # Примеры
            'совет', 'рекомендация', 'правило', 'принцип'  # Советы
        ]
        practical_score = sum(1 for word in practical_indicators if word in quote.lower()) / len(practical_indicators)
        
        # Проверка на эмоциональность
        emotional_words = ['успех', 'победа', 'достижение', 'результат', 'эффект', 'мощный', 'сильный']
        emotional_score = sum(1 for word in emotional_words if word in quote.lower()) / len(emotional_words)
        
        # Определяем тип цитаты
        if len(quote) > 300:
            quote_type = QuoteType.FULL_PARAGRAPH
        elif len(quote) > 150:
            quote_type = QuoteType.HALF_PARAGRAPH
        else:
            quote_type = QuoteType.SPECIFIC_QUOTE
        
        # Улучшенная оценка качества
        context_score = min(len(quote) / len(full_context), 1.0) if full_context else 0.5
        overall_score = (length_score + completeness_score + meaningful_score + practical_score + emotional_score) / 5
        
        if overall_score >= 0.8:
            quality = QuoteQuality.EXCELLENT
        elif overall_score >= 0.6:
            quality = QuoteQuality.GOOD
        elif overall_score >= 0.4:
            quality = QuoteQuality.AVERAGE
        else:
            quality = QuoteQuality.POOR
        
        # Определяем категорию и аудиторию
        if business_score > 0.3:
            category = "business"
            target_audience = "entrepreneurs, marketers"
        elif action_score > 0.3:
            category = "action"
            target_audience = "practitioners"
        else:
            category = "general"
            target_audience = "general"
        
        # Определяем тональность
        if emotional_score > 0.3:
            sentiment = "motivational"
        elif practical_score > 0.3:
            sentiment = "practical"
        else:
            sentiment = "analytical"
        
        # Создаем объяснение
        reasoning_parts = []
        if meaningful_score > 0.3:
            reasoning_parts.append("содержит ключевые бизнес-термины")
        if practical_score > 0.3:
            reasoning_parts.append("имеет практическую ценность")
        if emotional_score > 0.3:
            reasoning_parts.append("вызывает эмоциональный отклик")
        if completeness_score > 0.8:
            reasoning_parts.append("завершенная мысль")
        
        reasoning = "Цитата " + ", ".join(reasoning_parts) if reasoning_parts else "Стандартная цитата"
        
        # Создаем краткую идею на основе анализа
        summary_parts = []
        if business_score > 0.3:
            summary_parts.append("бизнес-стратегия")
        if action_score > 0.3:
            summary_parts.append("практические действия")
        if result_score > 0.3:
            summary_parts.append("достижение результатов")
        if practical_score > 0.3:
            summary_parts.append("практические советы")
        if emotional_score > 0.3:
            summary_parts.append("мотивация")
        
        summary = "О " + ", ".join(summary_parts) if summary_parts else "Общая информация"
        
        return QuoteAnalysis(
            text=quote,
            quote_type=quote_type,
            quality=quality,
            confidence=overall_score,
            context_score=context_score,
            practical_value=practical_score,
            completeness=completeness_score,
            target_audience=target_audience,
            category=category,
            sentiment=sentiment,
            reasoning=reasoning,
            summary=summary
        )
    
    def extract_smart_quotes(self, text_chunks: List[str], page_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Извлекает умные цитаты из текстовых фрагментов
        
        Args:
            text_chunks: Список текстовых фрагментов
            page_numbers: Соответствующие номера страниц
            
        Returns:
            Список структурированных цитат
        """
        all_quotes = []
        
        for chunk, page_num in zip(text_chunks, page_numbers):
            # Разбиваем на абзацы
            paragraphs = re.split(r'\n\s*\n', chunk)
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                    
                # Анализируем абзац
                analyses = self.analyze_paragraph(paragraph, page_num)
                
                for analysis in analyses:
                    if analysis.quality in [QuoteQuality.EXCELLENT, QuoteQuality.GOOD]:
                        quote_data = {
                            "page": page_num,
                            "original": paragraph,
                            "quote": analysis.text,
                            "translated": analysis.text,  # Пока без перевода
                            "summary": analysis.summary,  # Краткая идея
                            "engaging": analysis.quality == QuoteQuality.EXCELLENT,
                            "category": analysis.category,
                            "style": "insight",
                            "meta": {
                                "sentiment": analysis.sentiment,
                                "target_audience": analysis.target_audience,
                                "length": len(analysis.text),
                                "confidence": analysis.confidence,
                                "context_score": analysis.context_score,
                                "practical_value": analysis.practical_value,
                                "completeness": analysis.completeness,
                                "quote_type": analysis.quote_type.value,
                                "reasoning": analysis.reasoning
                            }
                        }
                        all_quotes.append(quote_data)
        
        # Убираем дубликаты и сортируем по качеству
        unique_quotes = []
        seen_quotes = set()
        
        for quote in sorted(all_quotes, key=lambda x: x['meta']['confidence'], reverse=True):
            quote_text = quote['quote'].strip()
            if quote_text not in seen_quotes:
                unique_quotes.append(quote)
                seen_quotes.add(quote_text)
        
        return unique_quotes


def test_smart_extractor():
    """Тестирование умного экстрактора"""
    extractor = SmartQuoteExtractor()
    
    # Тестовый абзац
    test_paragraph = """
    Воронка продаж — это системный подход к привлечению и конвертации клиентов. 
    Она состоит из нескольких этапов: привлечение внимания, формирование интереса, 
    создание желания и побуждение к действию. Каждый этап требует особого подхода 
    и инструментов. Важно понимать, что воронка — это не просто последовательность 
    шагов, а целостная система взаимодействия с клиентом.
    """
    
    analyses = extractor.analyze_paragraph(test_paragraph, 1)
    
    print("Результаты анализа:")
    for i, analysis in enumerate(analyses, 1):
        print(f"\n{i}. {analysis.text[:100]}...")
        print(f"   Качество: {analysis.quality.value}")
        print(f"   Уверенность: {analysis.confidence:.2f}")
        print(f"   Тип: {analysis.quote_type.value}")
        print(f"   Объяснение: {analysis.reasoning}")


if __name__ == "__main__":
    test_smart_extractor()
