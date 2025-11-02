"""
Страница настроек и управления аккаунтом Threads
"""

import streamlit as st
import os
import requests
from dotenv import load_dotenv, set_key
from pathlib import Path

load_dotenv()

# Настройка страницы
st.set_page_config(
    page_title="Настройки - Threads API",
    page_icon="⚙️",
    layout="wide"
)

# Темная тема (такая же как в основном приложении)
st.markdown("""
<style>
    :root {
        --primary: #6366F1;
        --secondary: #EC4899;
        --success: #10B981;
        --bg-dark: #0F172A;
        --surface: #1E293B;
        --text: #F1F5F9;
    }

    .stApp {
        background: linear-gradient(135deg, #020617 0%, #0F172A 100%);
        color: var(--text);
    }

    h1 {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .profile-card {
        background: var(--surface);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }

    .status-ok {
        background: rgba(16, 185, 129, 0.1);
        border-left: 4px solid #10B981;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    .status-error {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid #EF4444;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    .info-item {
        background: #1E293B;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid var(--primary);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# ⚙️ Настройки и Профиль")

# Получаем текущие данные из .env
ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID") or os.getenv("IG_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Табы
tab1, tab2, tab3 = st.tabs(["👤 Профиль Threads", "🔑 API Ключи", "🧪 Тесты"])

# ========================================
# TAB 1: Профиль Threads
# ========================================
with tab1:
    st.markdown("## 👤 Ваш профиль Threads")

    if not ACCESS_TOKEN or not THREADS_USER_ID:
        st.error("❌ Threads API не настроен. Перейдите на вкладку '🔑 API Ключи' для настройки.")
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            # Кнопка проверки токена
            if st.button("🔍 Проверить токен", type="primary", use_container_width=True):
                with st.spinner("Проверяем токен..."):
                    try:
                        # Запрос к Threads API
                        response = requests.get(
                            f"https://graph.threads.net/v1.0/me",
                            params={
                                "fields": "id,username,name,threads_profile_picture_url,threads_biography",
                                "access_token": ACCESS_TOKEN
                            },
                            timeout=10
                        )

                        if response.status_code == 200:
                            profile_data = response.json()

                            st.markdown('<div class="status-ok">', unsafe_allow_html=True)
                            st.success("✅ Токен активен и работает!")
                            st.markdown('</div>', unsafe_allow_html=True)

                            # Отображаем профиль
                            st.markdown("---")
                            st.markdown("### 📊 Информация о профиле")

                            profile_col1, profile_col2 = st.columns([1, 2])

                            with profile_col1:
                                # Аватар
                                avatar_url = profile_data.get("threads_profile_picture_url")
                                if avatar_url:
                                    st.image(avatar_url, width=150)

                            with profile_col2:
                                st.markdown(f"""
                                <div class="info-item">
                                    <strong>👤 Имя:</strong> {profile_data.get('name', 'N/A')}
                                </div>
                                <div class="info-item">
                                    <strong>@Username:</strong> @{profile_data.get('username', 'N/A')}
                                </div>
                                <div class="info-item">
                                    <strong>🆔 User ID:</strong> {profile_data.get('id', 'N/A')}
                                </div>
                                """, unsafe_allow_html=True)

                            # Биография
                            bio = profile_data.get("threads_biography")
                            if bio:
                                st.markdown("### 📝 Биография")
                                st.info(bio)

                            # Сохраняем данные в session_state для отображения
                            st.session_state.profile_data = profile_data

                        elif response.status_code == 400:
                            error_data = response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown error")

                            st.markdown('<div class="status-error">', unsafe_allow_html=True)
                            st.error(f"❌ Токен истёк или невалиден")
                            st.markdown('</div>', unsafe_allow_html=True)

                            st.warning(f"**Ошибка:** {error_msg}")
                            st.info("""
                            **Что делать:**
                            1. Перейдите на вкладку '🔑 API Ключи'
                            2. Получите новый токен через Meta Developer Console
                            3. Обновите THREADS_ACCESS_TOKEN
                            """)

                        else:
                            st.error(f"❌ Ошибка {response.status_code}: {response.text}")

                    except requests.exceptions.Timeout:
                        st.error("❌ Таймаут. Проверьте интернет-соединение.")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")

        with col2:
            # Текущие настройки
            st.markdown("### 🔧 Текущие настройки")

            st.markdown(f"""
            <div class="info-item">
                <strong>User ID:</strong><br>
                <code>{THREADS_USER_ID[:15]}...</code>
            </div>
            <div class="info-item">
                <strong>Token:</strong><br>
                <code>{ACCESS_TOKEN[:20]}...</code>
            </div>
            """, unsafe_allow_html=True)

        # Если профиль уже загружен, показываем его
        if "profile_data" in st.session_state:
            st.markdown("---")
            st.markdown("### ✅ Последний успешный профиль")

            data = st.session_state.profile_data
            st.json(data)

# ========================================
# TAB 2: API Ключи
# ========================================
with tab2:
    st.markdown("## 🔑 Управление API ключами")

    st.info("""
    ⚠️ **Важно:** После изменения ключей перезапустите приложение для применения изменений.
    """)

    # Форма для Threads API
    with st.expander("📱 Threads API", expanded=True):
        st.markdown("### Настройки Threads API")

        new_access_token = st.text_input(
            "Access Token",
            value=ACCESS_TOKEN or "",
            type="password",
            help="Получите токен через Meta Developer Console"
        )

        new_user_id = st.text_input(
            "User ID",
            value=THREADS_USER_ID or "",
            help="ID вашего профиля в Threads"
        )

        if st.button("💾 Сохранить Threads API", type="primary"):
            env_path = Path(".env")

            if new_access_token:
                set_key(env_path, "THREADS_ACCESS_TOKEN", new_access_token)
            if new_user_id:
                set_key(env_path, "THREADS_USER_ID", new_user_id)
                set_key(env_path, "IG_USER_ID", new_user_id)

            st.success("✅ Настройки сохранены! Перезапустите приложение для применения.")

            st.info("""
            **Перезапуск:**
            ```bash
            # Остановите приложение (Ctrl+C)
            # Затем запустите снова:
            streamlit run app_gemini.py
            ```
            """)

    # Форма для Gemini API
    with st.expander("🧠 Google Gemini API", expanded=False):
        st.markdown("### Настройки Gemini API")

        new_gemini_key = st.text_input(
            "Gemini API Key",
            value=GEMINI_API_KEY or "",
            type="password",
            help="Получите ключ на https://aistudio.google.com/app/apikey"
        )

        if st.button("💾 Сохранить Gemini API", type="primary"):
            env_path = Path(".env")

            if new_gemini_key:
                set_key(env_path, "GEMINI_API_KEY", new_gemini_key)

            st.success("✅ Gemini API ключ сохранён! Перезапустите приложение.")

    # Инструкции
    st.markdown("---")
    st.markdown("### 📚 Как получить токены")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Threads API Token:**
        1. Перейдите на [Meta Developer Console](https://developers.facebook.com/)
        2. Выберите ваше приложение Threads
        3. Tools → Graph API Explorer
        4. Сгенерируйте токен с правами:
           - `threads_basic`
           - `threads_content_publish`
        5. Скопируйте токен и User ID
        """)

    with col2:
        st.markdown("""
        **Gemini API Key:**
        1. Перейдите на [Google AI Studio](https://aistudio.google.com/app/apikey)
        2. Нажмите "Create API Key"
        3. Выберите проект или создайте новый
        4. Скопируйте ключ
        """)

# ========================================
# TAB 3: Тесты
# ========================================
with tab3:
    st.markdown("## 🧪 Тестирование API")

    # Тест Threads API
    st.markdown("### 📱 Тест Threads API")

    if st.button("🧪 Тест: Получить профиль", use_container_width=True):
        if not ACCESS_TOKEN:
            st.error("❌ Токен не найден")
        else:
            with st.spinner("Тестируем..."):
                try:
                    response = requests.get(
                        f"https://graph.threads.net/v1.0/me",
                        params={
                            "fields": "id,username",
                            "access_token": ACCESS_TOKEN
                        },
                        timeout=10
                    )

                    st.markdown(f"**Status Code:** {response.status_code}")

                    if response.status_code == 200:
                        st.success("✅ API работает!")
                        st.json(response.json())
                    else:
                        st.error("❌ Ошибка API")
                        st.json(response.json())

                except Exception as e:
                    st.error(f"❌ Исключение: {e}")

    st.markdown("---")

    # Тест Gemini API
    st.markdown("### 🧠 Тест Gemini API")

    if st.button("🧪 Тест: Простой запрос к Gemini", use_container_width=True):
        if not GEMINI_API_KEY:
            st.error("❌ Gemini ключ не найден")
        else:
            with st.spinner("Тестируем Gemini..."):
                try:
                    import google.generativeai as genai

                    genai.configure(api_key=GEMINI_API_KEY)
                    model = genai.GenerativeModel('gemini-2.5-flash')

                    response = model.generate_content("Скажи привет одним словом")

                    st.success("✅ Gemini API работает!")
                    st.info(f"**Ответ:** {response.text}")

                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")

    st.markdown("---")

    # Тест публикации (с подтверждением)
    st.markdown("### 🚀 Тест публикации в Threads")

    test_message = st.text_area(
        "Тестовое сообщение",
        value="🧪 Тест публикации из Gemini Book Analyzer",
        max_chars=500
    )

    st.warning("⚠️ **Внимание:** Это реально опубликует пост в ваш Threads аккаунт!")

    confirm = st.checkbox("Я подтверждаю публикацию тестового поста")

    if confirm and st.button("🚀 Опубликовать тестовый пост", type="primary", use_container_width=True):
        if not ACCESS_TOKEN:
            st.error("❌ Токен не найден")
        else:
            with st.spinner("Публикуем..."):
                try:
                    # ШАГ 1: Создание контейнера
                    st.info("📝 Создаём черновик...")
                    container_response = requests.post(
                        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",
                        data={
                            "media_type": "TEXT",
                            "text": test_message,
                            "access_token": ACCESS_TOKEN
                        },
                        timeout=30
                    )

                    if container_response.status_code == 200:
                        container_data = container_response.json()
                        container_id = container_data.get('id')
                        st.success(f"✅ Черновик создан: {container_id}")

                        # ШАГ 2: Публикация
                        st.info("🚀 Публикуем...")
                        publish_response = requests.post(
                            f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
                            data={
                                "creation_id": container_id,
                                "access_token": ACCESS_TOKEN
                            },
                            timeout=30
                        )

                        if publish_response.status_code == 200:
                            publish_data = publish_response.json()
                            st.success(f"✅ Пост опубликован!")
                            st.info(f"**Post ID:** {publish_data.get('id')}")
                            st.json(publish_data)
                        else:
                            st.error(f"❌ Ошибка публикации {publish_response.status_code}")
                            st.json(publish_response.json())
                    else:
                        st.error(f"❌ Ошибка создания черновика {container_response.status_code}")
                        st.json(container_response.json())

                except Exception as e:
                    st.error(f"❌ Исключение: {e}")

# Footer
st.markdown("---")
st.caption("💡 **Совет:** Регулярно проверяйте токены, чтобы избежать ошибок при публикации.")
