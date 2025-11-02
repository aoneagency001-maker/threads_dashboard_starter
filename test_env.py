#!/usr/bin/env python3
"""
Проверка загрузки .env и работы Gemini
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("🔍 ПРОВЕРКА ОКРУЖЕНИЯ")
print("=" * 60)

# Загружаем .env
load_dotenv()

# Проверяем ключ
gemini_key = os.getenv("GEMINI_API_KEY")

if gemini_key:
    print(f"✅ GEMINI_API_KEY загружен")
    print(f"   Длина: {len(gemini_key)} символов")
    print(f"   Начало: {gemini_key[:20]}...")
else:
    print("❌ GEMINI_API_KEY не найден!")
    exit(1)

# Тестируем импорт
try:
    import google.generativeai as genai
    print("✅ google.generativeai импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    exit(1)

# Тестируем конфигурацию
try:
    genai.configure(api_key=gemini_key)
    print("✅ Gemini API сконфигурирован")
except Exception as e:
    print(f"❌ Ошибка конфигурации: {e}")
    exit(1)

# Тестируем создание модели
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("✅ Модель gemini-2.5-flash создана")
except Exception as e:
    print(f"❌ Ошибка создания модели: {e}")
    exit(1)

# Тестируем запрос
try:
    print("\n📝 Отправляем тестовый запрос...")
    response = model.generate_content("Ответь одним словом: да или нет?")
    print(f"✅ Ответ получен: {response.text}")
except Exception as e:
    print(f"❌ Ошибка запроса: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("=" * 60)
