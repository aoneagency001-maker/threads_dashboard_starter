"""
Многоэтапная валидация цитат для публикации в Threads.

Этапы валидации:
1. Базовая валидация (длина, структура, запрещенные слова)
2. Проверка осмысленности (завершенность мысли, контекст)
3. Оптимизация для Threads (длина до 500 символов, читабельность)
4. Финальная проверка качества
"""

import re
from typing import Dict, Any, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class ValidationStage(Enum):
    """Этапы валидации"""
    BASIC = "basic"
    MEANINGFULNESS = "meaningfulness"
    THREADS_OPTIMIZATION = "threads_optimization"
    FINAL_QUALITY = "final_quality"


class ValidationStatus(Enum):
    """Статус валидации"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    OPTIMIZED = "optimized"


@dataclass
class ValidationResult:
    """Результат валидации на определенном этапе"""
    stage: ValidationStage
    status: ValidationStatus
    message: str
    quote: str
    score: float  # 0.0 - 1.0
    details: Dict[str, Any]


class QuoteValidator:
    """Многоэтапный валидатор цитат"""

    # Ограничения для Threads
    THREADS_MAX_LENGTH = 500
    MIN_MEANINGFUL_LENGTH = 30
    OPTIMAL_LENGTH_RANGE = (100, 400)

    # Запрещенные паттерны
    FORBIDDEN_PATTERNS = [
        r"scan to download",
        r"www\.",
        r"https?://",
        r"глава\s+\d+",
        r"оглавление",
        r"содержание",
        r"page\s+\d+",
        r"стр\.\s*\d+",
        r"©",
        r"copyright",
        r"\bизд\b",
        r"издательство",
    ]

    # Маркеры незавершенной мысли
    INCOMPLETE_MARKERS = [
        r"\.\.\.$",  # троеточие в конце
        r",\s*$",     # запятая в конце
        r":\s*$",     # двоеточие в конце
        r"—\s*$",     # тире в конце
        r"\*\s*$",    # звездочка в конце
    ]

    def __init__(self, use_ai: bool = True):
        """
        Args:
            use_ai: Использовать ли AI для глубокой проверки осмысленности
        """
        self.use_ai = use_ai

    def validate_full_pipeline(self, quote_data: Dict[str, Any]) -> Tuple[bool, Dict[str, ValidationResult]]:
        """
        Полный пайплайн валидации цитаты

        Returns:
            (passed, results_by_stage)
        """
        results = {}
        quote_text = quote_data.get("quote", "").strip()

        # Этап 1: Базовая валидация
        result = self._validate_basic(quote_text)
        results[ValidationStage.BASIC] = result
        if result.status == ValidationStatus.FAILED:
            return False, results
        quote_text = result.quote

        # Этап 2: Проверка осмысленности
        result = self._validate_meaningfulness(quote_text, quote_data)
        results[ValidationStage.MEANINGFULNESS] = result
        if result.status == ValidationStatus.FAILED:
            return False, results
        quote_text = result.quote

        # Этап 3: Оптимизация для Threads
        result = self._optimize_for_threads(quote_text, quote_data)
        results[ValidationStage.THREADS_OPTIMIZATION] = result
        quote_text = result.quote

        # Этап 4: Финальная проверка качества
        result = self._validate_final_quality(quote_text, quote_data)
        results[ValidationStage.FINAL_QUALITY] = result

        passed = all(
            r.status in [ValidationStatus.PASSED, ValidationStatus.OPTIMIZED, ValidationStatus.WARNING]
            for r in results.values()
        )

        return passed, results

    def _validate_basic(self, quote: str) -> ValidationResult:
        """Этап 1: Базовая валидация структуры и содержания"""
        details = {}
        score = 1.0

        # Проверка длины
        length = len(quote)
        details["length"] = length

        if length < self.MIN_MEANINGFUL_LENGTH:
            return ValidationResult(
                stage=ValidationStage.BASIC,
                status=ValidationStatus.FAILED,
                message=f"Цитата слишком короткая ({length} символов, минимум {self.MIN_MEANINGFUL_LENGTH})",
                quote=quote,
                score=0.0,
                details=details
            )

        if length > self.THREADS_MAX_LENGTH:
            score *= 0.5
            details["too_long"] = True

        # Проверка запрещенных паттернов
        forbidden_found = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, quote, re.IGNORECASE):
                forbidden_found.append(pattern)

        if forbidden_found:
            details["forbidden_patterns"] = forbidden_found
            return ValidationResult(
                stage=ValidationStage.BASIC,
                status=ValidationStatus.FAILED,
                message=f"Найдены запрещенные паттерны: {', '.join(forbidden_found)}",
                quote=quote,
                score=0.0,
                details=details
            )

        # Проверка на пустоту и мусор
        if not quote or quote.isspace():
            return ValidationResult(
                stage=ValidationStage.BASIC,
                status=ValidationStatus.FAILED,
                message="Пустая цитата",
                quote=quote,
                score=0.0,
                details=details
            )

        # Очистка лишних пробелов
        cleaned_quote = re.sub(r'\s+', ' ', quote).strip()
        details["cleaned"] = cleaned_quote != quote

        return ValidationResult(
            stage=ValidationStage.BASIC,
            status=ValidationStatus.PASSED,
            message="Базовая валидация пройдена",
            quote=cleaned_quote,
            score=score,
            details=details
        )

    def _validate_meaningfulness(self, quote: str, quote_data: Dict[str, Any]) -> ValidationResult:
        """Этап 2: Проверка осмысленности и завершенности"""
        details = {}
        score = 1.0

        # Проверка завершенности предложения
        has_proper_ending = quote.endswith(('.', '!', '?', '…', '"', "'"))
        details["has_proper_ending"] = has_proper_ending

        if not has_proper_ending:
            score *= 0.3
            details["ending_issue"] = "Нет правильного окончания"

        # Проверка маркеров незавершенности
        incomplete_markers = []
        for pattern in self.INCOMPLETE_MARKERS:
            if re.search(pattern, quote):
                incomplete_markers.append(pattern)

        if incomplete_markers:
            details["incomplete_markers"] = incomplete_markers
            score *= 0.2

        # Проверка наличия глаголов (признак полноценного предложения)
        # Простая эвристика для русского языка
        verb_patterns = [
            r'\b\w+(ать|ить|еть|уть|ют|ит|ет|ут|ят|ат)\b',  # инфинитивы и 3-е лицо
            r'\b\w+(ал|ил|ел|ала|ила|ела|али|или|ели)\b',  # прошедшее время
        ]
        has_verbs = any(re.search(p, quote, re.IGNORECASE) for p in verb_patterns)
        details["has_verbs"] = has_verbs

        if not has_verbs:
            score *= 0.7
            details["verb_issue"] = "Возможно, не полное предложение (нет глаголов)"

        # Проверка на минимальное количество слов
        words = quote.split()
        word_count = len(words)
        details["word_count"] = word_count

        if word_count < 5:
            return ValidationResult(
                stage=ValidationStage.MEANINGFULNESS,
                status=ValidationStatus.FAILED,
                message=f"Слишком мало слов ({word_count}), не похоже на осмысленную цитату",
                quote=quote,
                score=0.0,
                details=details
            )

        # Проверка на наличие осмысленного содержания
        # (не только числа, символы и короткие слова)
        meaningful_words = [w for w in words if len(w) > 3 and not w.isdigit()]
        meaningful_ratio = len(meaningful_words) / word_count if word_count > 0 else 0
        details["meaningful_words_ratio"] = meaningful_ratio

        if meaningful_ratio < 0.5:
            score *= 0.5
            details["content_issue"] = "Мало осмысленных слов"

        # Итоговая оценка осмысленности
        if score < 0.5:
            return ValidationResult(
                stage=ValidationStage.MEANINGFULNESS,
                status=ValidationStatus.FAILED,
                message="Цитата не прошла проверку на осмысленность",
                quote=quote,
                score=score,
                details=details
            )
        elif score < 0.8:
            return ValidationResult(
                stage=ValidationStage.MEANINGFULNESS,
                status=ValidationStatus.WARNING,
                message="Цитата прошла с предупреждениями",
                quote=quote,
                score=score,
                details=details
            )

        return ValidationResult(
            stage=ValidationStage.MEANINGFULNESS,
            status=ValidationStatus.PASSED,
            message="Цитата осмысленная и завершенная",
            quote=quote,
            score=score,
            details=details
        )

    def _optimize_for_threads(self, quote: str, quote_data: Dict[str, Any]) -> ValidationResult:
        """Этап 3: Оптимизация для публикации в Threads"""
        details = {}
        score = 1.0
        optimized_quote = quote

        length = len(quote)
        details["original_length"] = length

        # Если цитата слишком длинная, обрезаем её умно
        if length > self.THREADS_MAX_LENGTH:
            # Пытаемся обрезать по предложениям
            sentences = re.split(r'(?<=[.!?])\s+', quote)
            optimized_quote = ""

            for sentence in sentences:
                if len(optimized_quote) + len(sentence) + 1 <= self.THREADS_MAX_LENGTH:
                    optimized_quote += (sentence + " ")
                else:
                    break

            optimized_quote = optimized_quote.strip()

            # Если не получилось собрать хотя бы одно предложение
            if len(optimized_quote) < self.MIN_MEANINGFUL_LENGTH:
                # Обрезаем по словам
                words = quote.split()
                optimized_quote = ""
                for word in words:
                    if len(optimized_quote) + len(word) + 1 <= self.THREADS_MAX_LENGTH - 3:
                        optimized_quote += (word + " ")
                    else:
                        break
                optimized_quote = optimized_quote.strip() + "..."

            details["was_truncated"] = True
            details["new_length"] = len(optimized_quote)
            score = 0.8

        # Проверка оптимальной длины
        opt_min, opt_max = self.OPTIMAL_LENGTH_RANGE
        if opt_min <= len(optimized_quote) <= opt_max:
            details["optimal_length"] = True
            score = min(score, 1.0)
        elif len(optimized_quote) < opt_min:
            details["shorter_than_optimal"] = True
            score *= 0.9
        else:
            details["longer_than_optimal"] = True
            score *= 0.95

        # Проверка читабельности (нет слишком длинных слов)
        words = optimized_quote.split()
        long_words = [w for w in words if len(w) > 20]
        if long_words:
            details["long_words"] = long_words
            score *= 0.9

        status = ValidationStatus.OPTIMIZED if length != len(optimized_quote) else ValidationStatus.PASSED

        return ValidationResult(
            stage=ValidationStage.THREADS_OPTIMIZATION,
            status=status,
            message=f"Цитата оптимизирована для Threads ({len(optimized_quote)} символов)",
            quote=optimized_quote,
            score=score,
            details=details
        )

    def _validate_final_quality(self, quote: str, quote_data: Dict[str, Any]) -> ValidationResult:
        """Этап 4: Финальная проверка качества"""
        details = {}
        score = 1.0

        # Собираем все оценки
        length = len(quote)
        details["final_length"] = length
        details["within_threads_limit"] = length <= self.THREADS_MAX_LENGTH

        # Проверяем качество из метаданных, если есть
        meta = quote_data.get("meta", {})
        if "confidence" in meta:
            confidence = meta["confidence"]
            details["confidence"] = confidence
            score *= confidence

        if "practical_value" in meta:
            practical_value = meta["practical_value"]
            details["practical_value"] = practical_value
            score *= (0.5 + practical_value * 0.5)  # 50% база + 50% от практической ценности

        if "completeness" in meta:
            completeness = meta["completeness"]
            details["completeness"] = completeness
            score *= (0.7 + completeness * 0.3)  # 70% база + 30% от завершенности

        # Проверка категории и стиля
        category = quote_data.get("category", "")
        style = quote_data.get("style", "")
        details["category"] = category
        details["style"] = style

        # Финальная оценка
        details["final_score"] = score

        if score < 0.5:
            return ValidationResult(
                stage=ValidationStage.FINAL_QUALITY,
                status=ValidationStatus.FAILED,
                message=f"Низкое итоговое качество (score: {score:.2f})",
                quote=quote,
                score=score,
                details=details
            )
        elif score < 0.7:
            return ValidationResult(
                stage=ValidationStage.FINAL_QUALITY,
                status=ValidationStatus.WARNING,
                message=f"Среднее качество (score: {score:.2f})",
                quote=quote,
                score=score,
                details=details
            )

        return ValidationResult(
            stage=ValidationStage.FINAL_QUALITY,
            status=ValidationStatus.PASSED,
            message=f"Отличное качество! (score: {score:.2f})",
            quote=quote,
            score=score,
            details=details
        )

    def get_validated_quote(self, quote_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Возвращает валидированную и оптимизированную цитату или None, если не прошла валидацию

        Returns:
            Обновленный quote_data с результатами валидации или None
        """
        passed, results = self.validate_full_pipeline(quote_data)

        if not passed:
            return None

        # Берем финальную цитату из последнего этапа оптимизации
        optimized_quote = results[ValidationStage.THREADS_OPTIMIZATION].quote

        # Обновляем данные цитаты
        updated_quote_data = {
            **quote_data,
            "quote": optimized_quote,
            "translated": optimized_quote,  # Обновляем и перевод
            "meta": {
                **quote_data.get("meta", {}),
                "validated": True,
                "validation_score": results[ValidationStage.FINAL_QUALITY].score,
                "threads_ready": True,
                "final_length": len(optimized_quote),
                "validation_stages": {
                    stage.value: {
                        "status": result.status.value,
                        "score": result.score,
                        "message": result.message,
                        "details": result.details
                    }
                    for stage, result in results.items()
                }
            }
        }

        return updated_quote_data
