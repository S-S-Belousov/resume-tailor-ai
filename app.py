import re
import hashlib
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
import extra_streamlit_components as stx

st.set_page_config(page_title="ResumeTailor AI", page_icon="📄", layout="centered")

# ---------- 1. СИСТЕМА ПЕРЕВОДОВ (i18n) ----------
TEXTS = {
    "ru": {
        "login_title": "🔐 Вход в ResumeTailor AI",
        "login_info": "Войдите или создайте аккаунт. При регистрации вам доступно 2 бесплатных анализа.",
        "email": "Ваш Email",
        "password": "Ваш Пароль",
        "btn_login": "Войти / Зарегистрироваться",
        "error_fill": "Пожалуйста, заполните оба поля.",
        "error_pwd": "Неверный пароль.",
        "success_reg": "Аккаунт создан!",
        "logout": "Выйти из аккаунта",
        "logged_as": "Вы вошли как",
        "how_it_works": "**Как это работает:** загрузи резюме → вставь текст вакансии → выбери тон → нажми «Анализировать».",
        "left": "Осталось бесплатно",
        "upload": "1️⃣ Загрузите резюме (PDF, DOCX или TXT)",
        "job_desc": "2️⃣ Вставьте текст вакансии",
        "tone": "3️⃣ Выберите стиль резюме",
        "tone_options": ["Профессиональный", "Креативный", "Краткий", "Акцент на достижениях"],
        "btn_analyze": "🔍 Анализировать",
        "warn_limit": "🚫 Бесплатные попытки закончились. Оформите подписку Pro ниже.",
        "spinner": "Нейросеть читает... ~15 секунд",
        "err_upload": "Сначала загрузите файл с резюме.",
        "err_job": "Вставьте текст вакансии.",
        "err_read": "Не удалось прочитать текст из файла.",
        "toast_ready": "✅ Анализ готов!",
        "ats_score": "**Оценка ATS:**",
        "btn_download": "💾 Скачать отчёт (.md)",
        "btn_copy": "📋 Нажмите на иконку справа, чтобы скопировать текст",
        "pro_active": "✅ У вас активна подписка Pro до",
        "pro_thanks": "Спасибо за поддержку!",
        "want_more": "### 💎 Хотите больше?",
        "pro_desc": "Оформите подписку **Pro** — неограниченные анализы.",
        "btn_buy": "Оформить подписку Pro (499 ₽/мес)",
        "feedback": "💬 Обратная связь"
    },
    "en": {
        "login_title": "🔐 Login to ResumeTailor AI",
        "login_info": "Sign in or create an account. You get 2 free analyses upon registration.",
        "email": "Your Email",
        "password": "Your Password",
        "btn_login": "Login / Register",
        "error_fill": "Please fill in both fields.",
        "error_pwd": "Incorrect password.",
        "success_reg": "Account created!",
        "logout": "Log out",
        "logged_as": "Logged in as",
        "how_it_works": "**How it works:** upload resume → paste job description → choose tone → click «Analyze».",
        "left": "Free tries left",
        "upload": "1️⃣ Upload your resume (PDF, DOCX or TXT)",
        "job_desc": "2️⃣ Paste the job description",
        "tone": "3️⃣ Choose resume tone",
        "tone_options": ["Professional", "Creative", "Concise", "Achievement-oriented"],
        "btn_analyze": "🔍 Analyze",
        "warn_limit": "🚫 Free tries exhausted. Please subscribe to Pro below.",
        "spinner": "AI is reading... ~15 seconds",
        "err_upload": "Please upload a resume file first.",
        "err_job": "Please paste the job description.",
        "err_read": "Could not read text from the file.",
        "toast_ready": "✅ Analysis ready!",
        "ats_score": "**ATS Match Score:**",
        "btn_download": "💾 Download report (.md)",
        "btn_copy": "📋 Click the icon on the right to copy",
        "pro_active": "✅ Your Pro subscription is active until",
        "pro_thanks": "Thank you for your support!",
        "want_more": "### 💎 Want more?",
        "pro_desc": "Subscribe to **Pro** — unlimited analyses.",
        "btn_buy": "Subscribe to Pro ($5/mo)",
        "feedback": "💬 Feedback"
    }
}

if 'lang' not in st.session_state:
    st.session_state.lang = "ru"
t = TEXTS[st.session_state.lang]

# ---------- 2. УПРАВЛЕНИЕ СЕССИЕЙ (COOKIES) ----------
# Инициализируем менеджер куки на самом верху
cookie_manager = stx.CookieManager(key="cookie_mgr")

# Проверяем куки ПЕРЕД рендером страницы
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email is None:
    saved_email = cookie_manager.get(cookie="rt_user_email")
    if saved_email:
        st.session_state.user_email = saved_email
        st.rerun() # Принудительный перезапуск, чтобы сразу пустить в кабинет

# ---------- 3. ПОДКЛЮЧЕНИЕ К SUPABASE ----------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"DB Error: {e}")
    st.stop()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- 4. АВТОРИЗАЦИЯ ----------
if not st.session_state.user_email:
    st.title(t["login_title"])
    st.info(t["login_info"])
    
    email_input = st.text_input(t["email"])
    password_input = st.text_input(t["password"], type="password")
    
    if st.button(t["btn_login"], type="primary"):
        if not email_input or not password_input:
            st.error(t["error_fill"])
        else:
            hashed_pwd = hash_password(password_input)
            response = supabase.table('user_subscriptions').select('*').eq('email', email_input).execute()
            
            if len(response.data) > 0:
                user = response.data[0]
                if user['password'] is None:
                    supabase.table('user_subscriptions').update({'password': hashed_pwd}).eq('email', email_input).execute()
                    st.session_state.user_email = email_input
                    cookie_manager.set("rt_user_email", email_input, expires_at=datetime.now(timezone.utc) + timedelta(days=30))
                    st.rerun()
                elif user['password'] == hashed_pwd:
                    st.session_state.user_email = email_input
                    cookie_manager.set("rt_user_email", email_input, expires_at=datetime.now(timezone.utc) + timedelta(days=30))
                    st.rerun()
                else:
                    st.error(t["error_pwd"])
            else:
                supabase.table('user_subscriptions').insert({'email': email_input, 'password': hashed_pwd, 'is_pro': False}).execute()
                st.session_state.user_email = email_input
                cookie_manager.set("rt_user_email", email_input, expires_at=datetime.now(timezone.utc) + timedelta(days=30))
                st.success(t["success_reg"])
                st.rerun()
    st.stop()

USER_EMAIL = st.session_state.user_email

# ---------- 5. БОКОВАЯ ПАНЕЛЬ ----------
with st.sidebar:
    st.markdown(f"👤 **{t['logged_as']}:**\n{USER_EMAIL}")
    st.divider()
    
    lang_choice = st.radio("🌐 Language / Язык", ["RU", "EN"], index=0 if st.session_state.lang == "ru" else 1, horizontal=True)
    if lang_choice == "RU" and st.session_state.lang != "ru":
        st.session_state.lang = "ru"
        st.rerun()
    elif lang_choice == "EN" and st.session_state.lang != "en":
        st.session_state.lang = "en"
        st.rerun()
        
    st.divider()
    st.link_button(t["feedback"], "https://t.me/your_telegram_username") # Замените на свой ник в ТГ или mailto
    
    st.divider()
    if st.button(t["logout"], use_container_width=True):
        st.session_state.user_email = None
        cookie_manager.delete("rt_user_email")
        st.rerun()

# ---------- 6. ПРОВЕРКА ПОДПИСКИ ----------
response = supabase.table('user_subscriptions').select('is_pro', 'valid_until').eq('email', USER_EMAIL).execute()
is_pro = False
sub_end_date = ""

if len(response.data) > 0:
    user_data = response.data[0]
    valid_until_str = user_data.get('valid_until')
    if user_data.get('is_pro') and valid_until_str:
        valid_until = datetime.fromisoformat(valid_until_str.replace('Z', '+00:00'))
        if valid_until > datetime.now(timezone.utc):
            is_pro = True
            sub_end_date = valid_until.strftime("%d.%m.%Y")

# ---------- 7. НЕЙРОСЕТЬ ----------
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except Exception:
    st.error("⚠️ API Key missing.")
    st.stop()

MODEL_NAME = "gemini-3.8-flash"

# ---------- 8. ЛИМИТЫ ----------
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

# ---------- 9. ФУНКЦИИ ----------
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

def analyze(resume_text, job_text, output_lang, tone):
    prompt = f"""You are an ATS (Applicant Tracking Systems) expert and career consultant.
Analyze the resume and the job description. YOU MUST ANSWER IN {output_lang.upper()}.
The improved resume and cover letter must be written in a {tone} tone.

=== RESUME ===
{resume_text}

=== JOB DESCRIPTION ===
{job_text}

Return the response STRICTLY in this markdown format (translate headers if output is English):

## 📊 Оценка соответствия / Match Score
Число от 0 до 100 и вердикт. / Number from 0 to 100 and a verdict.

## 🔑 Ключевые слова из вакансии / Key Keywords
Список. / List.

## ✅ Что уже хорошо / What is good
3–5 пунктов. / 3-5 points.

## ⚠️ Что исправить / What to improve
3–7 рекомендаций. / 3-7 recommendations.

## 📝 Улучшенная версия резюме / Improved Resume Version
Перепиши резюме, добавив ключевые слова, используя {tone} tone. / Rewrite the resume, adding keywords, using {tone} tone.

## ✉️ Сопроводительное письмо / Cover Letter
150–200 слов, {tone} tone. / 150-200 words, {tone} tone.
"""
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text

# ---------- 10. ИНТЕРФЕЙС ----------
st.title("📄 ResumeTailor AI")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(t["how_it_works"])
with col2:
    st.metric(t["left"], left_text)

st.divider()

uploaded = st.file_uploader(t["upload"], type=["pdf", "docx", "txt"])
job_text = st.text_area(t["job_desc"], height=200)

# Выбор тона
tone_selection = st.selectbox(t["tone"], t["tone_options"])

if disabled:
    st.warning(t["warn_limit"])

if st.button(t["btn_analyze"], type="primary", disabled=disabled):
    if not uploaded:
        st.error(t["err_upload"])
    elif not job_text.strip():
        st.error(t["err_job"])
    else:
        with st.spinner(t["spinner"]):
            try:
                resume_text = extract_text(uploaded)
                if not resume_text.strip():
                    st.error(t["err_read"])
                else:
                    output_lang = "Russian" if st.session_state.lang == "ru" else "English"
                    result = analyze(resume_text, job_text, output_lang, tone_selection)
                    st.session_state.results = result
                    if not is_pro:
                        st.session_state.used += 1
                    st.toast(t["toast_ready"])
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# ---------- 11. РЕЗУЛЬТАТ ----------
if st.session_state.get("results"):
    st.divider()
    st.markdown(st.session_state.results)
    
    match = re.search(r"(\d{1,3})\s*%", st.session_state.results)
    if match:
        score = min(int(match.group(1)), 100)
        st.divider()
        st.markdown(f"{t['ats_score']} {score}%")
        st.progress(score / 100)
    
    # НОВОЕ: Скачивание и копирование
    col_dl, col_empty = st.columns([1, 2])
    with col_dl:
        st.download_button(t["btn_download"], data=st.session_state.results, file_name="resume_analysis.md", mime="text/markdown")
    
    st.markdown(t["btn_copy"])
    st.code(st.session_state.results, language="markdown") # Блок с кнопкой копирования

# ---------- 12. ОПЛАТА ----------
st.divider()
if is_pro:
    st.success(f"{t['pro_active']} **{sub_end_date}**. {t['pro_thanks']}")
else:
    st.markdown(t["want_more"])
    st.markdown(t["pro_desc"])
    payment_link = "https://app.lava.top/products/4eaedb98-cd63-44be-ac78-4f2525920fab"
    st.link_button(t["btn_buy"], url=payment_link, type="primary")
