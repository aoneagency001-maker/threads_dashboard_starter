"""
Streamlit приложение для анализа книг с Gemini AI.
Фокус: структурированное извлечение инсайтов по главам и методам.
"""

import streamlit as st
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from backend.parser import BOOKS_DIR, QUOTES_DIR
from backend.gemini_book_analyzer import GeminiBookAnalyzer

# Загружаем переменные окружения
load_dotenv()

# Threads API credentials
ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("THREADS_USER_ID") or os.getenv("IG_USER_ID")


def publish_to_threads(caption: str) -> bool:
    """Публикует текстовый пост в Threads через официальный Threads API (двухэтапный процесс)."""
    if not ACCESS_TOKEN or not IG_USER_ID:
        st.error("❌ Токен Threads не найден. Добавьте THREADS_ACCESS_TOKEN и THREADS_USER_ID в .env файл.")
        return False

    try:
        # ШАГ 1: Создание контейнера (draft)
        st.info("📝 Создаём черновик поста...")
        container_response = requests.post(
            f"https://graph.threads.net/v1.0/{IG_USER_ID}/threads",
            data={
                "media_type": "TEXT",
                "text": caption,
                "access_token": ACCESS_TOKEN
            },
            timeout=30
        )

        if container_response.status_code != 200:
            error_data = container_response.json() if container_response.text else {}
            error_msg = error_data.get("error", {}).get("message", container_response.text[:200])

            # Проверяем на истекший токен
            if "expired" in error_msg.lower() or "Session has expired" in error_msg:
                st.error("❌ Токен Threads истёк!")
                st.warning("""
                **Как обновить токен:**
                1. Получите новый токен через Meta Developer Console
                2. Обновите `THREADS_ACCESS_TOKEN` в файле `.env`
                3. Перезапустите приложение

                **Или публикуйте вручную:** скопируйте текст инсайта и опубликуйте через приложение Threads.
                """)
            else:
                st.error(f"❌ Ошибка создания черновика ({container_response.status_code}): {error_msg}")

            return False

        container_data = container_response.json()
        if "id" not in container_data:
            st.error(f"❌ Черновик создан, но ID не получен: {container_data}")
            return False

        container_id = container_data["id"]
        st.info(f"✅ Черновик создан: {container_id}")

        # ШАГ 2: Публикация контейнера
        st.info("🚀 Публикуем пост...")
        publish_response = requests.post(
            f"https://graph.threads.net/v1.0/{IG_USER_ID}/threads_publish",
            data={
                "creation_id": container_id,
                "access_token": ACCESS_TOKEN
            },
            timeout=30
        )

        if publish_response.status_code == 200:
            publish_data = publish_response.json()
            if "id" in publish_data:
                post_id = publish_data["id"]
                st.success(f"✅ Пост успешно опубликован в Threads! 📱")
                st.info(f"**Post ID:** {post_id}")
                return True
            else:
                st.error(f"❌ Публикация завершена, но ID не получен: {publish_data}")
                return False
        else:
            error_data = publish_response.json() if publish_response.text else {}
            error_msg = error_data.get("error", {}).get("message", publish_response.text[:200])
            st.error(f"❌ Ошибка публикации ({publish_response.status_code}): {error_msg}")
            return False

    except requests.exceptions.Timeout:
        st.error("❌ Таймаут при публикации. Проверьте интернет-соединение.")
        return False
    except Exception as e:
        st.error(f"❌ Исключение при публикации: {str(e)}")
        return False


# Настройка страницы
st.set_page_config(
    page_title="Gemini Book Analyzer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Темная тема
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

    .insight-card {
        background: var(--surface);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .insight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(99, 102, 241, 0.2);
        border-color: var(--primary);
    }

    .badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .badge-category {
        background: linear-gradient(135deg, var(--primary), #818CF8);
        color: white;
    }

    .badge-method {
        background: linear-gradient(135deg, var(--secondary), #F472B6);
        color: white;
    }

    .badge-actionable {
        background: var(--success);
        color: white;
    }

    .chapter-header {
        background: var(--surface);
        border-left: 4px solid var(--primary);
        padding: 1rem 1.5rem;
        margin: 1.5rem 0 1rem 0;
        border-radius: 8px;
    }

    .stat-card {
        background: var(--surface);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }

    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown("# 🧠 Gemini Book Analyzer")
st.caption("Структурированный анализ книг: главы → методы → инсайты")

# Sidebar
with st.sidebar:
    st.markdown("## 📖 Выбор книги")

    pdf_files = sorted([p for p in BOOKS_DIR.glob("*.pdf")])
    pdf_names = [p.name for p in pdf_files]

    if not pdf_names:
        st.error("❌ PDF файлы не найдены в data/books/")
        st.stop()

    selected_name = st.selectbox(
        "Книга",
        options=pdf_names,
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("## ⚡ Действия")

    analyze_btn = st.button(
        "🚀 Анализировать книгу",
        type="primary",
        use_container_width=True,
        help="Извлечь все инсайты с помощью Gemini AI"
    )

    st.markdown("---")
    st.markdown("## 🔍 Фильтры")

    # Фильтры будут активны только если есть данные
    filter_category = st.selectbox(
        "Категория",
        options=["Все категории"] + GeminiBookAnalyzer.CATEGORIES
    )

    filter_method = st.selectbox(
        "Тип метода",
        options=["Все методы"] + GeminiBookAnalyzer.METHOD_TYPES
    )

    filter_actionable = st.checkbox("Только практичные", value=False)

    st.markdown("---")
    st.markdown("## 📡 Threads API")

    # Показываем статус подключения
    if ACCESS_TOKEN and IG_USER_ID:
        st.success("✅ Подключено")
        st.caption(f"User ID: {IG_USER_ID[:10]}...")
    else:
        st.warning("⚠️ Не настроено")
        st.caption("Добавьте THREADS_ACCESS_TOKEN и THREADS_USER_ID в .env")

# Определяем пути
selected_pdf = BOOKS_DIR / selected_name
book_stem = Path(selected_name).stem.replace(" ", "-")
analysis_json_path = QUOTES_DIR / f"{book_stem}_gemini_analysis.json"

# Обработка кнопки анализа
if analyze_btn:
    with st.spinner("🧠 Анализируем книгу с Gemini AI... Это может занять 2-5 минут..."):
        try:
            analyzer = GeminiBookAnalyzer()
            result_path = analyzer.analyze_pdf(str(selected_pdf))
            st.success(f"✅ Анализ завершен! Результат: {result_path}")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка анализа: {e}")
            import traceback
            st.code(traceback.format_exc())

# Загрузка и отображение данных
if analysis_json_path.exists():
    with open(analysis_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Статистика сверху
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{data['total_chapters']}</div>
            <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 0.5rem;">Глав</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{data['total_insights']}</div>
            <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 0.5rem;">Инсайтов</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        actionable = data['statistics']['actionable_count']
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{actionable}</div>
            <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 0.5rem;">Практичных</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        high_value = data['statistics']['high_value_count']
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{high_value}</div>
            <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 0.5rem;">Высокой ценности</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Табы для разных представлений
    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 По главам",
        "🏷️ По категориям",
        "🔧 По методам",
        "📊 Все инсайты"
    ])

    # Применяем фильтры
    def filter_insights(insights_list):
        filtered = insights_list

        if filter_category != "Все категории":
            filtered = [i for i in filtered if i.get('category') == filter_category]

        if filter_method != "Все методы":
            filtered = [i for i in filtered if i.get('method_type') == filter_method]

        if filter_actionable:
            filtered = [i for i in filtered if i.get('actionable') is True]

        return filtered

    # Функция отображения инсайта
    def display_insight(insight, show_chapter=True, unique_id=0):
        badges_html = f"""
        <span class="badge badge-category">{insight.get('category', 'N/A')}</span>
        <span class="badge badge-method">{insight.get('method_type', 'N/A')}</span>
        """

        if insight.get('actionable'):
            badges_html += '<span class="badge badge-actionable">✓ Практично</span>'

        if show_chapter:
            badges_html += f'<span class="badge" style="background: #334155;">📖 Глава {insight.get("chapter_num")}</span>'

        value_score = insight.get('practical_value', 0)
        value_color = "#10B981" if value_score >= 0.7 else "#F59E0B" if value_score >= 0.5 else "#94A3B8"

        card_html = f"""
        <div class="insight-card">
            <div style="margin-bottom: 1rem;">{badges_html}</div>
            <h3 style="color: #F1F5F9; margin-bottom: 0.5rem;">{insight.get('title', 'Без названия')}</h3>
            <p style="font-size: 1.1rem; line-height: 1.6; color: #E2E8F0; margin-bottom: 1rem;">
                {insight.get('text', '')}
            </p>
            <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 1rem;">
                {insight.get('description', '')}
            </p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #94A3B8; font-size: 0.85rem;">
                    📏 Длина: {insight.get('length', 0)} символов
                </span>
                <span style="color: {value_color}; font-weight: 600; font-size: 0.85rem;">
                    💎 Ценность: {value_score:.0%}
                </span>
            </div>
        </div>
        """

        st.markdown(card_html, unsafe_allow_html=True)

        # Кнопки для работы с инсайтом
        insight_text = insight.get('text', '')

        col1, col2 = st.columns([1, 1])

        with col1:
            # Кнопка копирования (всегда доступна)
            if insight_text:
                copy_key = f"copy_{unique_id}_{hash(insight_text) % 10000}"
                if st.button("📋 Копировать текст", key=copy_key, use_container_width=True):
                    # Используем st.code для возможности копирования
                    st.code(insight_text, language=None)
                    st.success("✅ Скопируйте текст выше")

        with col2:
            # Кнопка публикации (только если длина подходит)
            if insight_text and len(insight_text) <= 500:  # Threads лимит
                publish_key = f"publish_{unique_id}_{hash(insight_text) % 10000}"

                if st.button(f"🚀 Опубликовать в Threads", key=publish_key, type="primary", use_container_width=True):
                    with st.spinner("Публикуем..."):
                        publish_to_threads(insight_text)
            elif insight_text:
                st.caption(f"⚠️ Слишком длинный для Threads ({len(insight_text)}/500 символов)")

    # TAB 1: По главам
    with tab1:
        st.markdown("### 📚 Инсайты по главам")

        for chapter in data['chapters']:
            # Получаем инсайты этой главы
            chapter_insights = [
                i for i in data['all_insights']
                if i.get('chapter_num') == chapter['chapter_num']
            ]

            # Применяем фильтры
            filtered_insights = filter_insights(chapter_insights)

            if not filtered_insights:
                continue

            # Заголовок главы
            st.markdown(f"""
            <div class="chapter-header">
                <h2 style="margin: 0; color: #F1F5F9;">
                    Глава {chapter['chapter_num']}: {chapter['title']}
                </h2>
                <p style="color: #94A3B8; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                    {len(filtered_insights)} инсайтов • {chapter['content_length']:,} символов
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Инсайты главы
            for idx, insight in enumerate(filtered_insights):
                display_insight(insight, show_chapter=False, unique_id=f"ch{chapter['chapter_num']}_{idx}")

    # TAB 2: По категориям
    with tab2:
        st.markdown("### 🏷️ Инсайты по категориям")

        for category, cat_data in data['by_category'].items():
            filtered_insights = filter_insights(cat_data['insights'])

            if not filtered_insights:
                continue

            with st.expander(f"**{category.upper()}** ({len(filtered_insights)} инсайтов)", expanded=True):
                for idx, insight in enumerate(filtered_insights):
                    display_insight(insight, unique_id=f"cat{category}_{idx}")

    # TAB 3: По методам
    with tab3:
        st.markdown("### 🔧 Инсайты по типам методов")

        method_names = {
            "framework": "🏗️ Фреймворки и системы",
            "rule": "📜 Правила и принципы",
            "technique": "🔧 Техники и методы",
            "mistake": "❌ Ошибки и что избегать",
            "case_study": "📝 Кейсы и примеры",
            "exercise": "💪 Упражнения",
            "insight": "💡 Инсайты и наблюдения"
        }

        for method_type, method_data in data['by_method'].items():
            filtered_insights = filter_insights(method_data['insights'])

            if not filtered_insights:
                continue

            method_label = method_names.get(method_type, method_type)

            with st.expander(f"**{method_label}** ({len(filtered_insights)} инсайтов)", expanded=True):
                for idx, insight in enumerate(filtered_insights):
                    display_insight(insight, unique_id=f"meth{method_type}_{idx}")

    # TAB 4: Все инсайты
    with tab4:
        st.markdown("### 📊 Все инсайты (хронологически)")

        filtered_all = filter_insights(data['all_insights'])

        st.caption(f"Показано {len(filtered_all)} из {data['total_insights']} инсайтов")

        for idx, insight in enumerate(filtered_all):
            display_insight(insight, unique_id=f"all_{idx}")

else:
    # Нет данных
    st.info("📚 Нажмите '🚀 Анализировать книгу' для начала работы")

    st.markdown("---")
    st.markdown("### ✨ Что умеет Gemini Book Analyzer?")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **🔍 Глубокий анализ:**
        - Автоматическое разбиение на главы
        - Извлечение всех ценных мыслей
        - Структурирование по методам
        - Оценка практической ценности
        """)

    with col2:
        st.markdown("""
        **🎯 Категоризация:**
        - Маркетинг, продажи, психология
        - Лидерство, финансы, стратегия
        - Фреймворки, техники, кейсы
        - Правила, ошибки, инсайты
        """)

    st.markdown("---")
    st.markdown("""
    **💡 Преимущества Gemini:**
    - ✅ Огромный контекст (до 2M токенов)
    - ✅ Очень низкая стоимость ($0.075/1M токенов)
    - ✅ Отличное качество анализа
    - ✅ Быстрая обработка целых книг
    """)
