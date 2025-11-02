import streamlit as st
import json
from pathlib import Path
from backend.parser import process_book, QUOTES_DIR, BOOKS_DIR
from backend.agent import refine_quotes, harvest_all_from_pdf, improve_existing_quotes, deep_scan_with_gemini
import requests
import os
from dotenv import load_dotenv
import asyncio
from threads_api.src.threads_api import ThreadsAPI

load_dotenv()

# Официальный Instagram Graph API
ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID") or os.getenv("THREADS_USER_ID")
THREADS_APP_ID = os.getenv("THREADS_APP_ID")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

# Неофициальная threads-api библиотека (логин/пароль)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Современная темная тема - Custom CSS
DARK_THEME_CSS = """
<style>
    /* Основные цвета темной темы */
    :root {
        --primary-color: #6366F1;
        --secondary-color: #EC4899;
        --success-color: #10B981;
        --warning-color: #F59E0B;
        --error-color: #EF4444;
        --bg-dark: #0F172A;
        --bg-darker: #020617;
        --surface: #1E293B;
        --surface-light: #334155;
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --border-color: #334155;
    }

    /* Фон приложения */
    .stApp {
        background: linear-gradient(135deg, var(--bg-darker) 0%, var(--bg-dark) 100%);
    }

    /* Sidebar стили */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
        border-right: 1px solid var(--border-color);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }

    /* Заголовки */
    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }

    h1 {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem !important;
        margin-bottom: 1.5rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
        margin-bottom: 1rem !important;
        border-bottom: 2px solid var(--primary-color);
        padding-bottom: 0.5rem;
    }

    h3 {
        font-size: 1.2rem !important;
        color: var(--text-secondary) !important;
    }

    /* Карточки цитат */
    .quote-card {
        background: var(--surface);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }

    .quote-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(99, 102, 241, 0.2);
        border-color: var(--primary-color);
    }

    /* Бейджи статусов */
    .badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .badge-engaging {
        background: linear-gradient(135deg, var(--primary-color), #818CF8);
        color: white;
    }

    .badge-improved {
        background: linear-gradient(135deg, var(--secondary-color), #F472B6);
        color: white;
    }

    .badge-normal {
        background: var(--surface-light);
        color: var(--text-secondary);
    }

    .badge-quality {
        background: var(--success-color);
        color: white;
    }

    /* Кнопки */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
        border: none;
        padding: 0.6rem 1.2rem;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary-color), #818CF8);
        color: white;
    }

    .stButton > button[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }

    .stButton > button[kind="secondary"] {
        background: var(--surface);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--surface-light);
        border-color: var(--primary-color);
    }

    /* Инпуты */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    /* Метрики */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: var(--primary-color) !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricDelta"] {
        color: var(--success-color) !important;
    }

    /* Статистические карточки */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }

    .stat-card {
        background: var(--surface);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        border-color: var(--primary-color);
        transform: translateY(-2px);
    }

    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .stat-label {
        color: var(--text-secondary);
        font-size: 0.875rem;
        margin-top: 0.5rem;
        font-weight: 600;
    }

    /* Разделители */
    hr {
        border-color: var(--border-color) !important;
        opacity: 0.3 !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: var(--surface) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary-color) !important;
    }

    /* Прогресс бар */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    }

    /* Спиннер */
    .stSpinner > div {
        border-top-color: var(--primary-color) !important;
    }

    /* Тексты */
    p, span, div {
        color: var(--text-primary);
    }

    .stMarkdown {
        color: var(--text-primary) !important;
    }

    /* Caption */
    .caption {
        color: var(--text-secondary);
        font-size: 0.875rem;
    }

    /* Success/Error/Warning/Info */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border-left: 4px solid var(--success-color) !important;
        color: var(--success-color) !important;
    }

    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border-left: 4px solid var(--error-color) !important;
        color: var(--error-color) !important;
    }

    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border-left: 4px solid var(--warning-color) !important;
        color: var(--warning-color) !important;
    }

    .stInfo {
        background: rgba(99, 102, 241, 0.1) !important;
        border-left: 4px solid var(--primary-color) !important;
        color: var(--primary-color) !important;
    }

    /* Качественные индикаторы */
    .quality-bar {
        height: 4px;
        border-radius: 2px;
        background: linear-gradient(90deg, var(--success-color), var(--warning-color), var(--error-color));
        margin-top: 0.5rem;
    }

    /* Секция метаданных */
    .metadata {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }

    .meta-item {
        background: var(--surface-light);
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
</style>
"""

def publish_to_threads(caption: str) -> bool:
    """Публикует текстовый пост в Threads через официальный Threads API."""
    if not ACCESS_TOKEN or not IG_USER_ID:
        st.error("❌ Токен Threads не найден. Добавь его в .env файл.")
        return False

    try:
        # Создание поста через Threads API (правильный endpoint)
        response = requests.post(
            f"https://graph.threads.net/v1.0/{IG_USER_ID}/threads",
            data={
                "media_type": "TEXT",
                "text": caption,
                "access_token": ACCESS_TOKEN
            },
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if "id" in response_data:
                post_id = response_data["id"]
                st.success(f"✅ Пост успешно опубликован в Threads! 📱\n**Post ID:** {post_id}")
                return True
            else:
                st.error(f"❌ Пост создан, но ID не получен: {response_data}")
                return False
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("error", {}).get("message", response.text[:200])
            st.error(f"❌ Ошибка публикации ({response.status_code}): {error_msg}")
            return False
            
    except requests.exceptions.Timeout:
        st.error("❌ Таймаут при публикации. Проверьте интернет-соединение.")
        return False
    except Exception as e:
        st.error(f"❌ Исключение при публикации: {str(e)}")
        return False

async def publish_to_threads_api_async(caption: str) -> bool:
    """Публикует текстовый пост в Threads через threads-api (неофициальный метод)."""
    api = ThreadsAPI()

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        st.error("❌ Учетные данные Instagram не найдены. Добавьте INSTAGRAM_USERNAME и INSTAGRAM_PASSWORD в .env файл.")
        return False

    try:
        # Логин с кешированием токена
        is_logged_in = await api.login(
            username=INSTAGRAM_USERNAME,
            password=INSTAGRAM_PASSWORD,
            cached_token_path=".token"
        )

        if not is_logged_in:
            st.error("❌ Ошибка авторизации в Threads. Проверьте учетные данные в .env файле.")
            await api.close_gracefully()
            return False

        # Публикация поста
        result = await api.post(caption=caption)

        if result and hasattr(result, 'media') and result.media.pk:
            st.success(f"✅ Пост успешно опубликован в Threads через threads-api!")
            st.info(f"📱 Post ID: {result.media.pk}")
            await api.close_gracefully()
            return True
        else:
            st.error("❌ Ошибка публикации поста через threads-api")
            await api.close_gracefully()
            return False

    except Exception as e:
        st.error(f"❌ Ошибка threads-api: {e}")
        await api.close_gracefully()
        return False

def publish_to_threads_api(caption: str) -> bool:
    """Синхронная обертка для публикации через threads-api."""
    return asyncio.run(publish_to_threads_api_async(caption))

# Настройка страницы
st.set_page_config(
    page_title="Quotes Extractor - База цитат",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Применяем темную тему
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# Главный заголовок с градиентом
st.markdown('<h1>📚 База цитат из книг</h1>', unsafe_allow_html=True)

# Sidebar с улучшенным дизайном
with st.sidebar:
    st.markdown('<h2>📖 Источник</h2>', unsafe_allow_html=True)
    pdf_files = sorted([p for p in BOOKS_DIR.glob("*.pdf")])
    pdf_names = [p.name for p in pdf_files]
    selected_name = st.selectbox("Выберите PDF книгу", options=pdf_names, label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<h2>🔍 Поиск</h2>', unsafe_allow_html=True)
    query = st.text_input("Поиск по цитатам", "", placeholder="Введите текст для поиска...", label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<h2>⚡ Действия</h2>', unsafe_allow_html=True)

    # НОВАЯ КНОПКА: Глубокое сканирование с Gemini
    deep_scan_btn = st.button("🚀 ГЛУБОКОЕ СКАНИРОВАНИЕ (Gemini)", type="primary", use_container_width=True, help="Извлекает ВСЕ инсайты из книги. Очень дешево!")

    st.markdown("---")
    st.caption("**Стандартные методы:**")
    insights_btn = st.button("🔥 Собрать цитаты (GPT)", type="secondary", use_container_width=True)
    improve_btn = st.button("🧠 Улучшить цитаты", use_container_width=True)

content_col, preview_col = st.columns([2, 1])

print(f"🐛 DEBUG: selected_name = {selected_name}")
print(f"🐛 DEBUG: deep_scan_btn = {deep_scan_btn}")

if selected_name:
    selected_pdf = BOOKS_DIR / selected_name
    quotes_json_path = QUOTES_DIR / (Path(selected_name).stem.replace(" ", "-") + ".json")

    # ГЛУБОКОЕ СКАНИРОВАНИЕ с Gemini
    if deep_scan_btn:
        print(f"\n{'='*60}")
        print(f"🚀 НАЧАЛО ГЛУБОКОГО СКАНИРОВАНИЯ")
        print(f"{'='*60}")
        print(f"📁 PDF путь: {selected_pdf}")
        print(f"💾 Выходной путь: {quotes_json_path}")

        with st.spinner("🚀 Глубокое сканирование книги с Gemini AI... Это займет 30-60 секунд..."):
            try:
                print("📞 Вызов deep_scan_with_gemini()...")
                result_path = deep_scan_with_gemini(str(selected_pdf))
                print(f"📥 Результат вызова: {result_path}")

                if result_path:
                    print(f"✅ Получен путь к результату: {result_path}")

                    # Загружаем результаты
                    with open(result_path, "r", encoding="utf-8") as f:
                        deep_data = json.load(f)

                    total_quotes = deep_data.get("total_quotes", 0)
                    print(f"📊 Извлечено цитат: {total_quotes}")
                    st.success(f"✅ Глубокое сканирование завершено! Извлечено {total_quotes} инсайтов из книги!")

                    # Копируем в основной файл цитат для отображения
                    with open(quotes_json_path, "w", encoding="utf-8") as f:
                        json.dump(deep_data, f, ensure_ascii=False, indent=2)

                    print(f"💾 Результаты сохранены в {quotes_json_path}")
                    st.balloons()
                    st.rerun()
                else:
                    print("❌ Функция вернула пустой путь")
                    st.error("❌ Не удалось выполнить глубокое сканирование. Проверьте логи.")
            except Exception as e:
                print(f"❌ ОШИБКА при глубоком сканировании: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                st.error(f"❌ Ошибка: {e}")

    if insights_btn:
        with st.spinner("🤖 Анализирую книгу и создаю осмысленные цитаты..."):
            out = harvest_all_from_pdf(str(selected_pdf))
        st.success(f"✅ Готово! Создано структурированных цитат: {out}")
        st.rerun()
    
    if improve_btn:
        if quotes_json_path.exists():
            with st.spinner("🧠 Улучшаю существующие цитаты с помощью умного анализа..."):
                out = improve_existing_quotes(str(quotes_json_path))
            st.success(f"✅ Готово! Улучшены цитаты: {out}")
            st.rerun()
        else:
            st.warning("Сначала соберите цитаты с помощью кнопки 'Собрать лучшие цитаты'")

    if quotes_json_path.exists():
        with open(quotes_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            data = payload.get("quotes", []) if isinstance(payload, dict) else payload
    else:
        data = []

    # Поиск/фильтр
    if query:
        q = query.lower()
        def match(item: dict) -> bool:
            return any(
                q in (item.get(k, "") or "").lower()
                for k in ("quote", "translated", "summary", "original")
            )
        filtered = [it for it in data if match(it)]
    else:
        filtered = data

    with content_col:
        st.markdown('<h2>📝 Цитаты</h2>', unsafe_allow_html=True)

        if not filtered:
            st.info("📚 Нет данных. Нажмите 'Собрать цитаты с AI' для анализа книги.")
        else:
            # Статистика в красивых карточках
            engaging_count = len([item for item in filtered if item.get("engaging") is True])
            improved_count = len([item for item in filtered if item.get("meta", {}).get("improved") is True])
            normal_count = len(filtered) - engaging_count - improved_count

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Всего цитат", len(filtered))
            with col2:
                st.metric("🔥 Осмысленные", engaging_count)
            with col3:
                st.metric("🧠 Улучшенные", improved_count)

            st.markdown("---")

            # Пагинация
            per_page = 5
            total = len(filtered)
            total_pages = (total + per_page - 1) // per_page if total else 1

            # Пагинация сверху
            col_page, col_info = st.columns([1, 2])
            with col_page:
                page = st.number_input("Страница", min_value=1, max_value=max(total_pages, 1), value=1, step=1, label_visibility="collapsed")
            with col_info:
                st.caption(f"Страница {page} из {total_pages} • Показано {min(per_page, total - (page-1)*per_page)} из {total} цитат")

            start = (page - 1) * per_page
            end = start + per_page

            # Отображаем цитаты как карточки
            for i, item in enumerate(filtered[start:end], start=start + 1):
                display_text = item.get('quote', '') or item.get('translated', '') or item.get('original', '')
                if not display_text:
                    continue

                meta = item.get("meta", {})
                is_improved = meta.get("improved", False)
                is_engaging = item.get("engaging") is True

                # Создаем карточку цитаты
                card_html = '<div class="quote-card">'

                # Заголовок карточки с бейджами
                badges = ""
                if is_engaging and is_improved:
                    badges = '<span class="badge badge-engaging">Осмысленная</span><span class="badge badge-improved">Улучшенная</span>'
                elif is_engaging:
                    badges = '<span class="badge badge-engaging">Осмысленная</span>'
                elif is_improved:
                    badges = '<span class="badge badge-improved">Улучшенная</span>'
                else:
                    badges = '<span class="badge badge-normal">Обычная</span>'

                card_html += f'<div style="margin-bottom: 1rem;">{badges}</div>'

                # Текст цитаты
                card_html += f'<div style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1rem; color: var(--text-primary);">"{display_text}"</div>'

                # Метаданные с индикатором длины для Threads
                meta_items = []
                if item.get("category"):
                    meta_items.append(f'<span class="meta-item">📂 {item.get("category")}</span>')
                if item.get("style"):
                    meta_items.append(f'<span class="meta-item">🎯 {item.get("style")}</span>')
                if meta.get("quote_type"):
                    meta_items.append(f'<span class="meta-item">📝 {meta.get("quote_type")}</span>')

                # Показываем длину с индикатором для Threads
                quote_length = len(display_text)
                threads_limit = 500
                length_color = "var(--success-color)" if quote_length <= threads_limit else "var(--error-color)"
                length_icon = "✓" if quote_length <= threads_limit else "⚠️"
                meta_items.append(
                    f'<span class="meta-item" style="color: {length_color};">'
                    f'{length_icon} Длина: {quote_length}/{threads_limit}'
                    f'</span>'
                )

                # Показываем validation score если есть
                if meta.get("validation_score"):
                    val_score = meta.get("validation_score")
                    meta_items.append(f'<span class="meta-item badge-quality">✓ Качество: {val_score:.0%}</span>')
                elif meta.get("confidence"):
                    conf_val = meta.get("confidence")
                    meta_items.append(f'<span class="meta-item">✓ Уверенность: {conf_val:.0%}</span>')

                # Индикатор валидации для Threads
                if meta.get("threads_ready"):
                    meta_items.append('<span class="badge badge-quality">✓ Готово для Threads</span>')

                if meta_items:
                    card_html += f'<div class="metadata">{"".join(meta_items)}</div>'

                card_html += '</div>'
                st.markdown(card_html, unsafe_allow_html=True)

                # Сводка под карточкой
                summary = item.get("summary")
                if summary:
                    st.markdown(f"**💡 Суть:** {summary}")

                # Дополнительная информация
                if meta.get("reasoning") or meta.get("validation_stages"):
                    with st.expander("🔍 Подробный анализ качества и валидации"):
                        # Показываем этапы валидации если есть
                        if meta.get("validation_stages"):
                            st.markdown("### ✅ Этапы валидации цитаты")
                            validation_stages = meta.get("validation_stages")

                            for stage_name, stage_data in validation_stages.items():
                                status = stage_data.get("status", "unknown")
                                score = stage_data.get("score", 0)
                                message = stage_data.get("message", "")

                                # Эмодзи для статуса
                                status_emoji = {
                                    "passed": "✅",
                                    "optimized": "🔧",
                                    "warning": "⚠️",
                                    "failed": "❌"
                                }.get(status, "❓")

                                st.markdown(f"**{status_emoji} {stage_name.upper()}** (score: {score:.0%})")
                                st.caption(message)

                                # Детали этапа
                                details = stage_data.get("details", {})
                                if details:
                                    detail_items = []
                                    for key, value in details.items():
                                        if isinstance(value, bool):
                                            detail_items.append(f"• {key}: {'✓' if value else '✗'}")
                                        elif isinstance(value, (int, float)):
                                            detail_items.append(f"• {key}: {value}")
                                        elif isinstance(value, str):
                                            detail_items.append(f"• {key}: {value}")
                                    if detail_items:
                                        st.text("\n".join(detail_items))
                                st.markdown("---")

                        # Объяснение если есть
                        if meta.get("reasoning"):
                            st.markdown("### 💡 Объяснение")
                            st.write(meta.get('reasoning'))

                        # Оценки качества
                        quality_metrics = []
                        if meta.get("context_score"):
                            quality_metrics.append(("Контекст", meta.get("context_score")))
                        if meta.get("practical_value"):
                            quality_metrics.append(("Практическая ценность", meta.get("practical_value")))
                        if meta.get("completeness"):
                            quality_metrics.append(("Завершенность", meta.get("completeness")))

                        if quality_metrics:
                            st.markdown("### 📊 Метрики качества")
                            cols = st.columns(len(quality_metrics))
                            for idx, (label, value) in enumerate(quality_metrics):
                                with cols[idx]:
                                    st.metric(label, f"{value:.0%}")

                # Номер страницы
                page_num = item.get("page")
                if page_num:
                    st.caption(f"📄 Страница {page_num}")

                st.markdown("<br>", unsafe_allow_html=True)

            # Кнопка публикации
            st.markdown("---")

            # Автоматический выбор метода публикации
            use_official_api = ACCESS_TOKEN and IG_USER_ID
            use_threads_api = INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD

            if use_official_api:
                api_method = "официальный Threads API (graph.threads.net)"
                st.success("✅ Официальный Threads API настроен и готов к публикации")
            elif use_threads_api:
                api_method = "threads-api (логин/пароль)"
                st.info("ℹ️ Используется неофициальный метод через threads-api")
            else:
                api_method = "не настроен"
                st.warning("⚠️ Метод публикации не настроен. Добавьте учетные данные в .env")

            st.caption(f"📡 Метод публикации: {api_method}")

            if st.button("🚀 Опубликовать в Threads", type="primary", use_container_width=True):
                if not use_official_api and not use_threads_api:
                    st.error("❌ Не настроен ни один метод публикации. Добавьте учетные данные в .env файл.")
                else:
                    with st.spinner("Публикуем пост..."):
                        selected = None
                        # Ищем engaging цитату
                        for it in filtered:
                            if it.get("engaging") is True and it.get("quote"):
                                selected = it.get("quote")
                                break
                        # Если нет engaging, берём первую доступную
                        if not selected and filtered:
                            selected = (filtered[0].get("quote") or filtered[0].get("translated") or "").strip()

                        if selected:
                            # Пробуем сначала официальный API, потом threads-api
                            if use_official_api:
                                publish_to_threads(selected)
                            elif use_threads_api:
                                publish_to_threads_api(selected)
                        else:
                            st.warning("Нет цитат для публикации. Сначала собери цитаты.")

    with preview_col:
        st.markdown('<h2>📊 Статистика</h2>', unsafe_allow_html=True)

        # Информация о файле
        st.markdown(f"""
        <div style="background: var(--surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 1rem;">
            <h3 style="margin-top: 0; color: var(--text-primary);">📖 Текущая книга</h3>
            <p style="color: var(--text-secondary); word-wrap: break-word;">{selected_pdf.name}</p>
        </div>
        """, unsafe_allow_html=True)

        # Статистика
        if data:
            st.markdown(f"""
            <div style="background: var(--surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color);">
                <h3 style="margin-top: 0; color: var(--text-primary);">📈 Обзор</h3>
                <div style="margin-bottom: 1rem;">
                    <div class="stat-value">{len(data)}</div>
                    <div class="stat-label">Всего цитат</div>
                </div>
                <div style="margin-bottom: 1rem;">
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--primary-color);">{engaging_count}</div>
                    <div class="stat-label">Осмысленных</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--secondary-color);">{improved_count}</div>
                    <div class="stat-label">Улучшенных</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
