import re
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
from st_paywall import add_auth  # <-- НОВОЕ

st.set_page_config(page_title="ResumeTailor AI", page_icon="📄", layout="centered")

# ---------- АВТОРИЗАЦИЯ И ПОДПИСКА ----------
# add_auth(required=False) означает: не блокировать приложение, если нет подписки.
# После вызова в st.session_state появятся:
# - st.session_state.email (email пользователя)
# - st.session_state.user_subscribed (True/False)
add_auth(required=False)

# ---------- ПОДКЛЮЧЕНИЕ НЕЙРОСЕТИ ----------
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except Exception:
    st.error("⚠️ Не найден API-ключ GEMINI_API_KEY.")
    st.stop()

MODEL_NAME = "gemini-3.8-flash"

# ---------- ЛОГИКА ЛИМИТОВ ----------
FREE_LIMIT = 2

# Инициализация счётчика в session_state, если его нет
if "used" not in st.session_state:
    st.session_state.used = 0

# Если пользователь подписан — лимита нет
if st.session_state.get("user_subscribed", False):
    disabled = False
    left_text = "∞"
else:
    left = max(FREE_LIMIT - st.session_state.used, 0)
    disabled = left <= 0
    left_text = f"{left} / {FREE_LIMIT}"

# ... (функции extract_text и analyze остаются без изменений) ...
def extract_text(uploaded_file):
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

def analyze(resume_text, job_text):
    prompt = f"""Ты — эксперт по ATS-системам и карьерный консультант. Проанализируй резюме и вакансию. Отвечай по-русски.
=== РЕЗЮМЕ ===
{resume_text}
=== ВАКАНСИЯ ===
{job_text}
Верни ответ в markdown:
## 📊 Оценка соответствия
Число от 0 до 100 и вердикт.
## 🔑 Ключевые слова из вакансии
Список.
## ✅ Что уже хорошо
3–5 пунктов.
## ⚠️ Что исправить
3–7 рекомендаций.
## 📝 Улучшенная версия резюме
Перепиши, добавив ключевые слова, но не выдумывай опыт.
## ✉️ Сопроводительное письмо
150–200 слов.
"""
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text

# ---------- ИНТЕРФЕЙС ----------
st.title("📄 ResumeTailor AI")

# Показываем email, если вошёл
if st.session_state.get("email"):
    st.caption(f"Вы вошли как: {st.session_state.email}")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("**Как это работает:** загрузи резюме → вставь текст вакансии → нажми «Анализировать».")
with col2:
    st.metric("Осталось бесплатно", left_text)

st.divider()

uploaded = st.file_uploader("1️⃣ Загрузите резюме (PDF, DOCX или TXT)", type=["pdf", "docx", "txt"])
job_text = st.text_area("2️⃣ Вставьте текст вакансии", height=250)

if disabled:
    st.warning("🚫 Бесплатные попытки закончились. Оформите подписку Pro ниже.")

if st.button("🔍 Анализировать", type="primary", disabled=disabled):
    if not uploaded:
        st.error("Сначала загрузите файл с резюме.")
    elif not job_text.strip():
        st.error("Вставьте текст вакансии.")
    else:
        with st.spinner("Нейросеть читает... ~15 секунд"):
            try:
                resume_text = extract_text(uploaded)
                if not resume_text.strip():
                    st.error("Не удалось прочитать текст из файла.")
                else:
                    result = analyze(resume_text, job_text)
                    st.session_state.results = result
                    # Увеличиваем счётчик, только если нет подписки
                    if not st.session_state.get("user_subscribed", False):
                        st.session_state.used += 1
                    st.toast("✅ Анализ готов!")
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

# ---------- ВЫВОД РЕЗУЛЬТАТА ----------
if st.session_state.get("results"):
    st.divider()
    st.markdown(st.session_state.results)
    match = re.search(r"(\d{1,3})\s*%", st.session_state.results)
    if match:
        score = min(int(match.group(1)), 100)
        st.divider()
        st.markdown(f"**Оценка ATS:** {score}%")
        st.progress(score / 100)
    st.download_button("💾 Скачать отчёт (.md)", data=st.session_state.results, file_name="resume_analysis.md", mime="text/markdown")

# ---------- БЛОК ОПЛАТЫ (ST-PAYWALL) ----------
st.divider()
if st.session_state.get("user_subscribed", False):
    st.success("✅ У вас активна подписка Pro. Спасибо за поддержку!")
else:
    st.markdown("### 💎 Хотите больше?")
    st.markdown("Оформите подписку **Pro** — неограниченные анализы.")
    # Кнопка ведёт на ссылку оплаты, которую мы создали в Stripe
    stripe_link = st.secrets.get("STRIPE_LINK", "#")
    st.link_button("Оформить подписку Pro ($9/мес)", url=stripe_link, type="primary")
