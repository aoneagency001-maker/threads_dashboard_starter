"""
Строгая валидация и фильтрация цитат
"""
import re
from typing import Dict, Any, Optional, Tuple
from .llm_client import get_llm_client
from .prompts import get_check_meaningfulness_prompts


class QuoteValidator:
    """Валидатор цитат с многоуровневой проверкой"""

    def __init__(self):
        self.llm_client = get_llm_client()

    def validate_quote(self, quote: str, context: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Полная валидация цитаты

        Args:
            quote: Текст цитаты для проверки
            context: Контекст (оригинальный абзац)

        Returns:
            (is_valid, validation_result)
        """
        # Уровень 1: Базовая валидация (быстро, без LLM)
        basic_valid, basic_result = self._basic_validation(quote)
        if not basic_valid:
            return False, basic_result

        # Уровень 2: Эвристическая проверка качества
        heuristic_valid, heuristic_result = self._heuristic_validation(quote)
        if not heuristic_valid:
            return False, heuristic_result

        # Уровень 3: LLM-проверка осмысленности (если доступно)
        if self.llm_client.is_available():
            llm_valid, llm_result = self._llm_validation(quote, context)
            if not llm_valid:
                return False, llm_result

            # Объединяем результаты
            return True, {**heuristic_result, **llm_result, "validation_level": "full"}

        # Если LLM недоступно, возвращаем результат эвристики
        return True, {**heuristic_result, "validation_level": "heuristic"}

    def _basic_validation(self, quote: str) -> Tuple[bool, Dict[str, Any]]:
        """Базовая проверка структуры цитаты"""
        result = {
            "stage": "basic",
            "errors": []
        }

        # Проверка на пустоту
        if not quote or not quote.strip():
            result["errors"].append("Пустая цитата")
            return False, result

        quote = quote.strip()

        # Проверка длины
        if len(quote) < 30:
            result["errors"].append(f"Слишком короткая: {len(quote)} символов (минимум 30)")
            return False, result

        if len(quote) > 250:
            result["errors"].append(f"Слишком длинная: {len(quote)} символов (максимум 250)")
            return False, result

        # Проверка на завершённость
        if not quote.endswith(('.', '!', '?', '…', '"', '»')):
            result["errors"].append("Незавершённая мысль (нет финальной пунктуации)")
            return False, result

        # Проверка на мусор
        junk_patterns = [
            (r'^(Глава|Страница|Раздел|Часть|Chapter|Page)\s+\d+', "Заголовок главы/страницы"),
            (r'(www\.|http://|https://|\.pdf|\.com|\.ru)', "Содержит ссылки"),
            (r'^(Оглавление|Содержание|Введение|Предисловие|Послесловие)', "Служебная часть книги"),
            (r'(Scan to download|Download free|Visit our website)', "Промо-текст"),
            (r'^\d+\.\s*\d+\.\s*\d+', "Нумерация (формат 1.2.3)"),
            (r'©\s*\d{4}|Copyright', "Копирайт"),
            (r'ISBN\s*[\d\-]+', "ISBN номер"),
        ]

        for pattern, error_msg in junk_patterns:
            if re.search(pattern, quote, re.IGNORECASE):
                result["errors"].append(error_msg)
                return False, result

        # Проверка на обрывки
        if quote.startswith(('...', '…', 'и ', 'а ', 'но ', 'то ', 'что ')):
            result["errors"].append("Начинается с середины предложения")
            return False, result

        # Всё ОК
        return True, result

    def _heuristic_validation(self, quote: str) -> Tuple[bool, Dict[str, Any]]:
        """Эвристическая проверка качества цитаты"""
        result = {
            "stage": "heuristic",
            "scores": {},
            "warnings": []
        }

        quote_lower = quote.lower()

        # Проверка на ключевые слова (маркетинг, бизнес, продажи)
        business_keywords = [
            'продаж', 'маркетинг', 'бизнес', 'клиент', 'доход', 'прибыль',
            'воронк', 'конвер', 'трафик', 'аудитори', 'оффер', 'продукт',
            'стратег', 'тактик', 'запуск', 'масштаб', 'рост', 'лид',
            'sales', 'marketing', 'business', 'customer', 'revenue', 'profit'
        ]

        action_keywords = [
            'важно', 'нужно', 'должен', 'можно', 'следует', 'необходимо',
            'делай', 'строй', 'создавай', 'тестируй', 'проверяй', 'анализируй',
            'понимай', 'избегай', 'используй', 'применяй', 'внедряй'
        ]

        value_keywords = [
            'результат', 'эффект', 'успех', 'проблема', 'решение',
            'метод', 'способ', 'техника', 'инструмент', 'система',
            'ошибка', 'урок', 'опыт', 'практик', 'совет'
        ]

        # Подсчёт совпадений
        business_score = sum(1 for kw in business_keywords if kw in quote_lower)
        action_score = sum(1 for kw in action_keywords if kw in quote_lower)
        value_score = sum(1 for kw in value_keywords if kw in quote_lower)

        result["scores"]["business_relevance"] = min(business_score / 3, 1.0)
        result["scores"]["actionability"] = min(action_score / 2, 1.0)
        result["scores"]["practical_value"] = min(value_score / 2, 1.0)

        # Проверка структуры предложения
        sentences = re.split(r'[.!?]+', quote)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) == 0:
            result["warnings"].append("Нет предложений")
            return False, result

        if len(sentences) > 4:
            result["warnings"].append(f"Слишком много предложений: {len(sentences)}")

        # Проверка на вводные фразы (плохой сигнал)
        intro_phrases = [
            'в этой главе', 'далее мы рассмотрим', 'теперь перейдём',
            'как мы уже говорили', 'в предыдущей главе', 'в заключение',
            'подводя итог', 'резюмируя', 'таким образом'
        ]

        for phrase in intro_phrases:
            if phrase in quote_lower:
                result["warnings"].append(f"Содержит вводную фразу: '{phrase}'")
                return False, result

        # Проверка на автора/биографию
        bio_patterns = [
            r'\bродился\b', r'\bокончил\b', r'\bучился\b',
            r'\bоснователь\b', r'\bавтор книг\b', r'\bпопулярный спикер\b'
        ]

        for pattern in bio_patterns:
            if re.search(pattern, quote_lower):
                result["warnings"].append("Похоже на биографию автора")
                return False, result

        # Минимальный порог качества
        avg_score = (
            result["scores"]["business_relevance"] +
            result["scores"]["actionability"] +
            result["scores"]["practical_value"]
        ) / 3

        if avg_score < 0.1:  # Слишком низкий балл
            result["warnings"].append(f"Низкая релевантность (score: {avg_score:.2f})")
            return False, result

        result["overall_score"] = avg_score
        return True, result

    def _llm_validation(self, quote: str, context: str) -> Tuple[bool, Dict[str, Any]]:
        """LLM-проверка осмысленности и качества"""
        system_prompt, user_prompt = get_check_meaningfulness_prompts(quote, context)

        response = self.llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_type="smart",  # Используем лучшую модель для проверки
            temperature=0.1,  # Низкая температура для стабильности
            response_format="json"
        )

        if not response:
            return True, {"llm_check": "unavailable"}

        result = self.llm_client.parse_json_response(response)
        if not result:
            return True, {"llm_check": "parse_error"}

        # Проверяем результат LLM
        is_meaningful = result.get("is_meaningful", False)
        quality = result.get("quality", "poor")

        # Строгая проверка: принимаем только excellent и good
        if quality in ["excellent", "good"] and is_meaningful:
            return True, {
                "llm_check": "passed",
                "quality": quality,
                "completeness": result.get("completeness", 0),
                "clarity": result.get("clarity", 0),
                "practical_value": result.get("practical_value", 0),
                "impact": result.get("impact", 0),
                "social_quality": result.get("social_quality", 0),
                "reasoning": result.get("reasoning", ""),
                "suggestion": result.get("suggestion", "")
            }
        else:
            return False, {
                "llm_check": "rejected",
                "quality": quality,
                "reasoning": result.get("reasoning", "Низкое качество"),
                "suggestion": result.get("suggestion", "")
            }

    def batch_validate(self, quotes: list, contexts: list = None) -> list:
        """
        Пакетная валидация цитат

        Args:
            quotes: Список цитат
            contexts: Список контекстов (опционально)

        Returns:
            Список валидированных цитат с метаданными
        """
        if contexts is None:
            contexts = [""] * len(quotes)

        validated = []
        for i, (quote, context) in enumerate(zip(quotes, contexts)):
            is_valid, validation_result = self.validate_quote(quote, context)

            if is_valid:
                validated.append({
                    "quote": quote,
                    "context": context,
                    "validation": validation_result,
                    "index": i
                })

        return validated


# Быстрые утилиты
def is_valid_quote(quote: str) -> bool:
    """Быстрая проверка: валидна ли цитата (только базовая и эвристическая)"""
    validator = QuoteValidator()
    basic_valid, _ = validator._basic_validation(quote)
    if not basic_valid:
        return False

    heuristic_valid, _ = validator._heuristic_validation(quote)
    return heuristic_valid


def get_quote_quality_score(quote: str) -> float:
    """Получить оценку качества цитаты (0-1)"""
    validator = QuoteValidator()

    basic_valid, _ = validator._basic_validation(quote)
    if not basic_valid:
        return 0.0

    heuristic_valid, heuristic_result = validator._heuristic_validation(quote)
    if not heuristic_valid:
        return 0.0

    return heuristic_result.get("overall_score", 0.0)


# Пример использования
if __name__ == "__main__":
    validator = QuoteValidator()

    test_quotes = [
        "Лучший продукт не всегда побеждает. Побеждает лучший маркетинг.",  # Отлично
        "Воронка продаж — это путь клиента от незнакомца до покупателя.",  # Отлично
        "В этой главе мы рассмотрим стратегии маркетинга...",  # Плохо (вводная фраза)
        "Рассел Брансон родился в 1980 году в штате Юта...",  # Плохо (биография)
        "...и поэтому это важно учитывать при...",  # Плохо (обрывок)
        "Очень экономный и эффективный способ найма низкоквалифицированных кадров и удаленных сотрудников. Иногда в регионах в группах ВКонтакте можно встретить опытных, сильных менеджеров. Не стоит выбирать «или  или». Хороший менеджер по продажам всегда себя окупит с лихвой..."  # Плохо (слишком длинно)
    ]

    print("=== ТЕСТИРОВАНИЕ ВАЛИДАТОРА ===\n")

    for i, quote in enumerate(test_quotes, 1):
        print(f"Цитата {i}: {quote[:80]}...")
        is_valid, result = validator.validate_quote(quote)

        print(f"Валидна: {is_valid}")
        if not is_valid and "errors" in result:
            print(f"Ошибки: {result['errors']}")
        if "warnings" in result:
            print(f"Предупреждения: {result['warnings']}")
        if "overall_score" in result:
            print(f"Оценка качества: {result['overall_score']:.2f}")

        print("-" * 80)
