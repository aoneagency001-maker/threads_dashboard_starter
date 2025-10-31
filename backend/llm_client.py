"""
Универсальный клиент для работы с различными LLM (Claude, OpenAI)
"""
import os
import json
from typing import Optional, Dict, Any, List
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class LLMProvider(Enum):
    """Поддерживаемые провайдеры LLM"""
    CLAUDE = "claude"
    OPENAI = "openai"
    AUTO = "auto"  # Автовыбор (приоритет: Claude -> OpenAI)


class LLMClient:
    """Универсальный клиент для работы с LLM"""

    def __init__(self, provider: LLMProvider = LLMProvider.AUTO):
        self.provider = provider
        self.claude_client = None
        self.openai_client = None

        # Получаем API ключи
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        # Инициализируем доступные клиенты
        if anthropic_key:
            try:
                from anthropic import Anthropic
                self.claude_client = Anthropic(api_key=anthropic_key)
                print("✅ Claude API инициализирован")
            except ImportError:
                print("⚠️ Библиотека 'anthropic' не установлена. Установите: pip install anthropic")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации Claude: {e}")

        if openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key)
                print("✅ OpenAI API инициализирован")
            except ImportError:
                print("⚠️ Библиотека 'openai' не установлена. Установите: pip install openai")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации OpenAI: {e}")

        # Определяем активного провайдера
        if provider == LLMProvider.AUTO:
            if self.claude_client:
                self.active_provider = LLMProvider.CLAUDE
                print("🎯 Выбран провайдер: Claude (приоритетный)")
            elif self.openai_client:
                self.active_provider = LLMProvider.OPENAI
                print("🎯 Выбран провайдер: OpenAI (fallback)")
            else:
                self.active_provider = None
                print("❌ Нет доступных LLM провайдеров!")
        else:
            self.active_provider = provider
            if provider == LLMProvider.CLAUDE and not self.claude_client:
                print("⚠️ Claude API не доступен, но указан в настройках")
            elif provider == LLMProvider.OPENAI and not self.openai_client:
                print("⚠️ OpenAI API не доступен, но указан в настройках")

    def is_available(self) -> bool:
        """Проверяет, доступен ли хотя бы один LLM провайдер"""
        return self.claude_client is not None or self.openai_client is not None

    def get_model_name(self, model_type: str = "default") -> str:
        """Возвращает название модели в зависимости от провайдера"""
        if self.active_provider == LLMProvider.CLAUDE:
            if model_type == "fast":
                return "claude-3-haiku-20240307"  # Быстрая и дешёвая
            elif model_type == "smart":
                return "claude-3-5-sonnet-20241022"  # Умная (по умолчанию)
            else:
                return "claude-3-5-sonnet-20241022"

        elif self.active_provider == LLMProvider.OPENAI:
            if model_type == "fast":
                return "gpt-4o-mini"
            elif model_type == "smart":
                return "gpt-4o"
            else:
                return "gpt-4o-mini"

        return None

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model_type: str = "default",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[str] = None
    ) -> Optional[str]:
        """
        Универсальный метод для общения с LLM

        Args:
            system_prompt: Системный промпт
            user_prompt: Запрос пользователя
            model_type: Тип модели ('default', 'fast', 'smart')
            temperature: Температура генерации (0-1)
            max_tokens: Максимальное количество токенов
            response_format: Формат ответа (None или 'json')

        Returns:
            Ответ модели или None при ошибке
        """
        if not self.is_available():
            print("❌ Нет доступных LLM провайдеров")
            return None

        model = self.get_model_name(model_type)

        try:
            # Claude API
            if self.active_provider == LLMProvider.CLAUDE and self.claude_client:
                response = self.claude_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.content[0].text

            # OpenAI API
            elif self.active_provider == LLMProvider.OPENAI and self.openai_client:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # Добавляем JSON mode только для OpenAI
                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.openai_client.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            else:
                print(f"❌ Провайдер {self.active_provider} не доступен")
                return None

        except Exception as e:
            print(f"❌ Ошибка при обращении к {self.active_provider.value}: {e}")
            return None

    def parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсит JSON ответ от LLM"""
        if not response:
            return None

        try:
            # Пытаемся распарсить как есть
            return json.loads(response)
        except json.JSONDecodeError:
            # Пытаемся найти JSON в тексте
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Пытаемся извлечь из markdown блока
            json_block = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_block:
                try:
                    return json.loads(json_block.group(1))
                except json.JSONDecodeError:
                    pass

            print(f"⚠️ Не удалось распарсить JSON ответ: {response[:200]}...")
            return None


# Глобальный инстанс (синглтон)
_global_client: Optional[LLMClient] = None


def get_llm_client(provider: LLMProvider = LLMProvider.AUTO) -> LLMClient:
    """Получить глобальный инстанс LLM клиента"""
    global _global_client
    if _global_client is None:
        _global_client = LLMClient(provider)
    return _global_client


def reset_llm_client():
    """Сбросить глобальный инстанс (для тестов)"""
    global _global_client
    _global_client = None


# Пример использования
if __name__ == "__main__":
    # Инициализация клиента
    client = get_llm_client(LLMProvider.AUTO)

    if client.is_available():
        # Тест с простым запросом
        response = client.chat(
            system_prompt="Ты эксперт по маркетингу.",
            user_prompt="Дай краткий совет по увеличению продаж (1 предложение)",
            model_type="smart",
            temperature=0.3
        )

        print("\n📝 Ответ модели:")
        print(response)

        # Тест с JSON ответом
        json_response = client.chat(
            system_prompt="Ты возвращаешь только валидный JSON.",
            user_prompt='Верни JSON с полями: {"совет": "текст совета", "категория": "маркетинг"}',
            model_type="smart",
            temperature=0.2,
            response_format="json"
        )

        print("\n📊 JSON ответ:")
        parsed = client.parse_json_response(json_response)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print("❌ LLM клиент не доступен. Проверьте API ключи в .env файле")
