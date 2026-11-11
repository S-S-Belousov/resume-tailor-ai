import re
import hashlib
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
from supabase import create_client, Client
from datetime import datetime, timezone

st.set_page_config(page_title="ResumeTailor AI", page_icon="📄", layout="centered")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Ошибка подключения к базе данных: {e}")
    st.stop()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- АВТОРИЗАЦИЯ ----------
if 'user_email' not in st.session_state or not st.session_state.user_email:
    st.title("🔐 Вход в ResumeTailor AI")
    st.info("Войдите или создайте аккаунт. При регистрации вам будет доступно 2 бесплатных анализа.")
    
    email_input = st.text_input("Ваш Email")
    password_input = st.text_input("Ваш Пароль", type="password")
    
    if st.button("Войти / Зарегистрироваться", type="primary"):
        if not email_input or not password_input:
            st.error("Пожалуйста, заполните оба поля.")
        else:
            hashed_pwd = hash_password(password_input)
            response = supabase.table('user_subscriptions').select('*').eq('email', email_input).execute()
            
            if len(response.data) > 0:
                user = response.data[0]
                if user['password'] is None:
                    supabase.table('user_subscriptions').update({'password': hashed_pwd}).eq('email', email_input).execute()
                    st.session_state.user_email = email_input
                    st.rerun()
                elif user['password'] == hashed_pwd:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.error("Неверный пароль.")
            else:
                supabase.table('user_subscriptions').insert({'email': email_input, 'password': hashed_pwd, 'is_pro': False}).execute()
                st.session_state.user_email = email_input
                st.success("Аккаунт создан!")
                st.rerun()
    st.stop()

USER_EMAIL = st.session_state.user_email

if st.sidebar.button("Выйти из аккаунта"):
    st.session_state.user_email = ""
    st.rerun()

# ---------- ПРОВЕРКА ПОДПИСКИ И ДАТЫ ----------
response = supabase.table('user_subscriptions').select('is_pro', 'valid_until').eq('email', USER_EMAIL).execute()
is_pro = False

if len(response.data) > 0:
    user_data = response.data[0]
    valid_until_str = user_data.get('valid_until')
    if user_data.get('is_pro') and valid_until_str:
        # Превращаем строку из базы в дату
        valid_until = datetime.fromisoformat(valid_until_str.replace('Z', '+00:00'))
        # Сравниваем с текущим временем
        if valid_until > datetime.now(timezone.utc):
            is_pro = True
            sub_end_date = valid_until.strftime("%d.%m.%Y")

# ---------- НЕЙРОСЕТЬ ----------
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except Exception:
    st.error("⚠️ Не найден API-ключ GEMINI_API_KEY.")
    st.stop()

MODEL_NAME = "gemini-3.8-flash"

# ---------- ЛИМИТЫ ----------
FREE_LIMIT = 2
if "used" not in st.session_state:
    st.session_state.used = 0

if is_pro:
    disabled = False
    left_text = "∞ (Pro)"
else:
    left = max(FREE_LIMIT - st.session_state.used, 0)
    disabled = left <= 0
    left_text = f"{left} / {FREE_LIMIT}"

# ---------- ФУНКЦИИ ----------
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
st.caption(f"Вы вошли как: {USER_EMAIL}")

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
                    if not is_pro:
                        st.session_state.used += 1
                    st.toast("✅ Анализ готов!")
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

# ---------- РЕЗУЛЬТАТ ----------
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

# ---------- ОПЛАТА ----------
st.divider()
if is_pro:
    st.success(f"✅ У вас активна подписка Pro до **{sub_end_date}**. Спасибо за поддержку!")
else:
    st.markdown("### 💎 Хотите больше?")
    st.markdown("Оформите подписку **Pro** — неограниченные анализы.")
    payment_link = "https://app.lava.top/products/4eaedb98-cd63-44be-ac78-4f2525920fab"
    st.link_button("Оформить подписку Pro (490 ₽/мес)", url=payment_link, type="primary")
