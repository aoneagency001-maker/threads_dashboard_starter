import streamlit as st
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from backend.database import get_db
from backend.parser_v2 import process_book, BOOKS_DIR

load_dotenv()
ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")


def publish_to_threads(caption: str, quote_id: int = None) -> bool:
    """Публикует текстовый пост в Threads через Instagram Graph API."""
    if not ACCESS_TOKEN or not IG_USER_ID:
        st.error("❌ Токен Threads не найден. Добавь его в .env файл.")
        return False

    create_media = requests.post(
        f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media",
        data={"caption": caption, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" not in create_media:
        st.error(f"Ошибка создания контейнера поста: {create_media}")
        return False

    creation_id = create_media["id"]

    publish = requests.post(
        f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" in publish:
        st.success("✅ Пост успешно опубликован в Threads!")
        # Отмечаем цитату как опубликованную в БД
        if quote_id:
            db = get_db()
            db.mark_as_published(quote_id)
        return True
    else:
        st.error(f"Ошибка публикации: {publish}")
        return False


# ============================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================

st.set_page_config(page_title="База цитат", page_icon="📚", layout="wide")
st.title("📚 База цитат из книг")

# ============================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================

db = get_db()

with st.sidebar:
    st.header("⚙️ Настройки")

    # Вкладки: Обзор, Обработка, Фильтры
    tab1, tab2, tab3 = st.tabs(["📊 Обзор", "📖 Обработка", "🔍 Фильтры"])

    with tab1:
        # Статистика по всей базе
        stats = db.get_statistics()
        st.metric("📚 Книг в базе", stats.get("total_books", 0))
        st.metric("💬 Всего цитат", stats.get("total_quotes", 0))
        st.metric("📝 Опубликовано", stats.get("published_quotes", 0))

        avg_quality = stats.get("avg_quality", 0.0)
        st.metric("⭐ Средняя оценка", f"{avg_quality:.2f}")

        st.divider()

        # Топ категории
        top_categories = stats.get("top_categories", [])
        if top_categories:
            st.write("**🏷️ Популярные категории:**")
            for cat, count in top_categories[:5]:
                st.write(f"• {cat}: {count}")

    with tab2:
        st.subheader("Обработать книгу")

        # Список PDF файлов
        pdf_files = sorted([p for p in BOOKS_DIR.glob("*.pdf")])
        pdf_names = ["(выберите PDF)"] + [p.name for p in pdf_files]
        selected_name = st.selectbox("Выберите PDF", options=pdf_names)

        if selected_name != "(выберите PDF)":
            selected_pdf = BOOKS_DIR / selected_name

            col1, col2 = st.columns(2)
            with col1:
                min_quotes = st.number_input("Мин. цитат", min_value=10, max_value=100, value=20)
            with col2:
                max_quotes = st.number_input("Макс. цитат", min_value=10, max_value=100, value=50)

            if st.button("🔥 Обработать книгу", type="primary", use_container_width=True):
                with st.spinner("🤖 Извлекаю и валидирую цитаты..."):
                    try:
                        output_path = process_book(str(selected_pdf), force=True)
                        if output_path:
                            st.success(f"✅ Книга обработана! Сохранено в: {output_path}")
                            st.info("💡 Перезапустите страницу для загрузки новых цитат в БД")
                        else:
                            st.error("❌ Ошибка обработки книги")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")

    with tab3:
        st.subheader("Фильтры")

        # Выбор книги
        books = db.get_all_books()
        book_options = ["(все книги)"] + [f"{b['title']}" for b in books]
        selected_book = st.selectbox("📚 Книга", options=book_options)

        if selected_book == "(все книги)":
            book_id = None
        else:
            # Находим ID книги
            book_id = next((b["id"] for b in books if b["title"] == selected_book), None)

        # Минимальное качество
        min_quality = st.slider("⭐ Мин. качество", 0.0, 1.0, 0.0, 0.1)

        # Категория
        categories = ["(все)"] + db.get_all_categories()
        selected_category = st.selectbox("🏷️ Категория", options=categories)
        category = None if selected_category == "(все)" else selected_category

        # Статус публикации
        publication_filter = st.radio(
            "📤 Статус",
            options=["Все", "Только неопубликованные", "Только опубликованные"]
        )

        only_unpublished = publication_filter == "Только неопубликованные"
        only_published = publication_filter == "Только опубликованные"

        # Поиск
        st.divider()
        search_query = st.text_input("🔎 Поиск по тексту", "")

# ============================================
# ОСНОВНОЙ КОНТЕНТ
# ============================================

# Получаем цитаты с учётом фильтров
if search_query:
    quotes = db.search_quotes(search_query)
else:
    quotes = db.get_quotes(
        book_id=book_id,
        category=category,
        min_quality=min_quality,
        only_unpublished=only_unpublished if not only_published else False
    )

    # Дополнительная фильтрация для опубликованных
    if only_published:
        quotes = [q for q in quotes if q.get("published_at")]

# Колонки для основного контента
content_col, actions_col = st.columns([3, 1])

with content_col:
    st.subheader(f"📝 Цитаты ({len(quotes)})")

    if not quotes:
        st.info("📚 Нет цитат по выбранным фильтрам. Попробуйте изменить параметры поиска.")
    else:
        # Пагинация
        per_page = 10
        total = len(quotes)
        total_pages = (total + per_page - 1) // per_page if total else 1
        page = st.number_input("Страница", min_value=1, max_value=max(total_pages, 1), value=1, step=1, key="page_num")
        start = (page - 1) * per_page
        end = start + per_page

        # Отображение цитат
        for idx, quote_item in enumerate(quotes[start:end], start=start + 1):
            quote_text = quote_item.get("quote", "")
            translated = quote_item.get("translated", "")
            quality = quote_item.get("quality", 0.0)
            category_name = quote_item.get("category", "general")
            published = quote_item.get("published_at")

            # Отображаемый текст (русский или оригинал)
            display_text = translated if translated else quote_text

            # Иконки статуса
            status_icons = []
            if quality >= 0.8:
                status_icons.append("🔥")
            if published:
                status_icons.append("✅")

            status_prefix = " ".join(status_icons) + " " if status_icons else ""

            # Заголовок цитаты
            st.markdown(f"**{idx}.** {status_prefix}{display_text}")

            # Метаданные
            meta_parts = []
            meta_parts.append(f"📂 {category_name}")
            meta_parts.append(f"⭐ {quality:.2f}")

            book_title = quote_item.get("book_title", "")
            if book_title:
                meta_parts.append(f"📚 {book_title}")

            page_num = quote_item.get("page")
            if page_num:
                meta_parts.append(f"📄 стр. {page_num}")

            if published:
                meta_parts.append(f"📤 Опубликовано")

            st.caption(" • ".join(meta_parts))

            # Развёрнутая информация
            with st.expander("🔍 Подробнее"):
                if quote_text != translated:
                    st.write(f"**Оригинал:** {quote_text}")

                summary = quote_item.get("summary", "")
                if summary:
                    st.write(f"**Суть:** {summary}")

                # Показываем метаданные из meta JSON поля
                meta_json = quote_item.get("meta", {})
                if meta_json:
                    st.write("**Метаданные:**")
                    for key, value in meta_json.items():
                        if isinstance(value, float):
                            st.write(f"• {key}: {value:.2f}")
                        else:
                            st.write(f"• {key}: {value}")

                # Кнопка публикации для этой конкретной цитаты
                if not published:
                    if st.button(f"📤 Опубликовать в Threads", key=f"publish_{quote_item['id']}"):
                        publish_to_threads(display_text, quote_item["id"])
                        st.rerun()

            st.divider()

with actions_col:
    st.subheader("⚡ Действия")

    if quotes:
        st.write(f"**Найдено:** {len(quotes)}")

        # Быстрая публикация лучшей цитаты
        if st.button("🚀 Опубликовать лучшую", type="primary", use_container_width=True):
            # Ищем лучшую неопубликованную цитату
            unpublished = [q for q in quotes if not q.get("published_at")]

            if unpublished:
                # Сортируем по качеству
                best = max(unpublished, key=lambda x: x.get("quality", 0.0))
                text = best.get("translated") or best.get("quote")

                if text:
                    with st.spinner("Публикуем..."):
                        publish_to_threads(text, best["id"])
                        st.rerun()
            else:
                st.warning("⚠️ Все цитаты уже опубликованы")

        # Экспорт
        st.divider()
        st.write("**📥 Экспорт:**")

        if st.button("💾 Скачать JSON", use_container_width=True):
            import json
            json_data = json.dumps(quotes, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ Скачать",
                data=json_data,
                file_name="quotes_export.json",
                mime="application/json",
                use_container_width=True
            )
    else:
        st.info("Выберите фильтры слева")

# ============================================
# ПОДВАЛ
# ============================================

st.divider()
st.caption("📚 База цитат из книг • Powered by Claude 3 Haiku • v2.0")
