# =====================================================
# ResumeTailor AI — MVP (обновлено для google-genai)
# =====================================================

import re
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

# ---------- 1. НАСТРОЙКА СТРАНИЦЫ ----------
st.set_page_config(
    page_title="ResumeTailor AI",
    page_icon="📄",
    layout="centered"
)

# ---------- 2. ПОДКЛЮЧЕНИЕ НЕЙРОСЕТИ (НОВЫЙ SDK) ----------
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except Exception:
    st.error(
        "⚠️ Не найден API-ключ. Добавь GEMINI_API_KEY в Secrets на Streamlit Cloud "
        "(см. инструкцию Этапа 3)."
    )
    st.stop()

MODEL_NAME = "gemini-3.8-flash"

# ---------- 3. ЛИМИТЫ ДЛЯ БЕСПЛАТНОГО ТАРИФА ----------
FREE_LIMIT = 2

if "used" not in st.session_state:
    st.session_state.used = 0
if "results" not in st.session_state:
    st.session_state.results = None

# ---------- 4. ФУНКЦИЯ ЧТЕНИЯ ФАЙЛА ----------
def extract_text(uploaded_file):
    """Достаёт текст из PDF / DOCX / TXT."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    return ""

# ---------- 5. ФУНКЦИЯ АНАЛИЗА (НОВЫЙ SDK) ----------
def analyze(resume_text, job_text):
    """Отправляет текст в Gemini и возвращает разбор в формате markdown."""
    prompt = f"""Ты — эксперт по ATS-системам (Applicant Tracking Systems) и карьерный консультант.
Проанализируй резюме кандидата и вакансию. Отвечай по-русски.

=== РЕЗЮМЕ КАНДИДАТА ===
{resume_text}

=== ОПИСАНИЕ ВАКАНСИИ ===
{job_text}

Верни ответ СТРОГО в таком формате (markdown):

## 📊 Оценка соответствия
Число от 0 до 100 и одно предложение вердикта. Пример: `72% — резюме неплохое, но не хватает ключевых технологий из вакансии.`

## 🔑 Ключевые слова из вакансии
Список навыков/технологий/слов, которые важны для этой вакансии.

## ✅ Что уже хорошо в резюме
3–5 пунктов сильных сторон относительно вакансии.

## ⚠️ Что нужно исправить или добавить
3–7 конкретных рекомендаций (какие слова добавить, что переписать).

## 📝 Улучшенная версия резюме
Перепиши резюме так, чтобы оно лучше проходило ATS: добавь недостающие ключевые слова,
сформулируй опыт в формате «действие → результат». НЕ выдумывай опыт, которого нет.

## ✉️ Сопроводительное письмо
Короткое (150–200 слов) письмо под эту вакансию, от первого лица.
"""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text

# ---------- 6. ИНТЕРФЕЙС (БЕЗ ИЗМЕНЕНИЙ) ----------
st.title("📄 ResumeTailor AI")
st.caption("Узнай, проходит ли твоё резюме ATS-фильтр, и получи улучшенную версию за 30 секунд.")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("**Как это работает:** загрузи резюме → вставь текст вакансии → нажми «Анализировать».")
with col2:
    left = max(FREE_LIMIT - st.session_state.used, 0)
    st.metric("Осталось бесплатно", f"{left} / {FREE_LIMIT}")

st.divider()

uploaded = st.file_uploader(
    "1️⃣ Загрузите резюме (PDF, DOCX или TXT)",
    type=["pdf", "docx", "txt"]
)

job_text = st.text_area(
    "2️⃣ Вставьте текст вакансии",
    height=250,
    placeholder="Скопируйте сюда описание вакансии с hh.ru, LinkedIn и т.д."
)

disabled = st.session_state.used >= FREE_LIMIT

if disabled:
    st.warning("🚫 Бесплатные попытки закончились. Ниже — кнопка для оформления подписки.")

if st.button("🔍 Анализировать", type="primary", disabled=disabled):
    if not uploaded:
        st.error("Сначала загрузите файл с резюме.")
    elif not job_text.strip():
        st.error("Вставьте текст вакансии.")
    else:
        with st.spinner("Нейросеть читает резюме и вакансию... ~15 секунд"):
            try:
                resume_text = extract_text(uploaded)
                if not resume_text.strip():
                    st.error("Не удалось прочитать текст из файла. Попробуйте PDF/DOCX/TXT с текстом (не сканы-картинки).")
                else:
                    result = analyze(resume_text, job_text)
                    st.session_state.results = result
                    st.session_state.used += 1
                    st.success("Готово!")
            except Exception as e:
                st.error(f"Ошибка при обращении к нейросети: {e}")

# ---------- 7. ВЫВОД РЕЗУЛЬТАТА ----------
if st.session_state.results:
    st.divider()
    st.markdown(st.session_state.results)

    match = re.search(r"(\d{1,3})\s*%", st.session_state.results)
    if match:
        score = min(int(match.group(1)), 100)
        st.divider()
        st.markdown(f"**Оценка соответствия ATS:** {score}%")
        st.progress(score / 100)

    st.download_button(
        "💾 Скачать отчёт (.md)",
        data=st.session_state.results,
        file_name="resume_analysis.md",
        mime="text/markdown"
    )

# ---------- 8. ЗАГЛУШКА ДЛЯ ОПЛАТЫ ----------
st.divider()
st.markdown("### 💎 Хотите больше?")
st.markdown(
    "Оформите подписку **Pro** — неограниченные анализы и приоритетная скорость.  \n"
    "*(Кнопка оплаты появится здесь на Этапе 4.)*"
)
