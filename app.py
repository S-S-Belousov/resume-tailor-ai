import re
import hashlib
import streamlit as st
import smtplib
import time
import random
import string
import os
import requests
from email.mime.text import MIMEText
from google import genai
from pypdf import PdfReader
from docx import Document
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
from fpdf import FPDF

# =====================================================
# 1. НАСТРОЙКА СТРАНИЦЫ И ПЕРЕВОДЫ
# =====================================================
st.set_page_config(page_title="ResumeTailor AI", page_icon="📄", layout="centered")

TEXTS = {
    "ru": {
        # --- Лендинг и вход ---
        "hero_title": "Узнайте, почему ваше резюме игнорируют",
        "hero_subtitle": "Более 75% резюме отсеиваются роботами (ATS) еще до просмотра рекрутером. Загрузите резюме и вакансию — наш ИИ покажет слабые места и перепишет текст так, чтобы вы получили собеседование.",
        "feat_1": "🎯 **Оценка соответствия:** узнайте свой шанс пройти ATS-фильтр (от 0 до 100%).",
        "feat_2": "🔑 **Ключевые слова:** найдите навыки, которые требует работодатель.",
        "feat_3": "📝 **Улучшенное резюме:** ИИ перепишет опыт в формате «действие → результат».",
        "feat_4": "✉️ **Сопроводительное письмо:** готовый текст под конкретную вакансию.",
        "feat_5": "📥 **Скачивание в PDF:** получите аккуратный файл для отправки.",
        "login_form_title": "Вход или Регистрация",
        "login_form_info": "Новым пользователям доступно 2 бесплатных анализа.",
        "email": "Ваш Email", "password": "Ваш Пароль",
        "btn_login": "Войти / Зарегистрироваться", "forgot_password": "Забыли пароль?",
        # --- Сброс пароля ---
        "reset_title": "🔑 Сброс пароля",
        "reset_step1": "Введите email, указанный при регистрации. Мы отправим вам код для сброса.",
        "send_code": "Отправить код", "code_sent": "Код отправлен! Проверьте почту.",
        "reset_step2": "Введите код из письма и ваш новый пароль.",
        "code": "Код из письма (6 цифр)", "new_password": "Новый пароль",
        "btn_reset": "Сбросить пароль", "btn_back": "Назад ко входу",
        "reset_success": "Пароль успешно изменен! Теперь вы можете войти.",
        "reset_not_found": "Пользователь с таким email не найден.",
        "error_code": "Неверный или просроченный код.",
        "error_fill": "Пожалуйста, заполните все поля.",
        "error_pwd": "Неверный пароль.", "success_reg": "Аккаунт создан!",
        # --- Приложение ---
        "logout": "Выйти из аккаунта", "logged_as": "Вы вошли как",
        "how_it_works": "**Как это работает:** загрузи резюме → вставь текст вакансии → выбери тон → нажми «Анализировать».",
        "left": "Осталось бесплатно", "upload": "1️⃣ Загрузите резюме (PDF, DOCX или TXT)",
        "job_desc": "2️⃣ Вставьте текст вакансии", "tone": "3️⃣ Выберите стиль резюме",
        "tone_options": ["Профессиональный", "Креативный", "Краткий", "Акцент на достижениях"],
        "btn_analyze": "🔍 Анализировать", "warn_limit": "🚫 Бесплатные попытки закончились. Оформите подписку Pro ниже.",
        "spinner": "Нейросеть читает... ~15 секунд", "err_upload": "Сначала загрузите файл с резюме.",
        "err_job": "Вставьте текст вакансии.", "err_read": "Не удалось прочитать текст из файла.",
        "toast_ready": "✅ Анализ готов!", "ats_score": "**Оценка ATS:**",
        "btn_download_pdf": "📥 Скачать резюме в PDF", "btn_download_md": "💾 Скачать отчёт (.md)", 
        "btn_copy": "📋 Нажмите на иконку справа, чтобы скопировать текст",
        "pro_active": "✅ У вас активна подписка Pro до", "pro_thanks": "Спасибо за поддержку!",
        "want_more": "### 💎 Хотите больше?", "pro_desc": "Оформите подписку **Pro** — неограниченные анализы.",
        "btn_buy": "Оформить подписку Pro (499 ₽/мес)", "feedback": "💬 Обратная связь",
        "try_example": "💡 Попробовать на тестовом примере (без загрузки файла)",
        "example_info": "Загружен пример резюме IT-специалиста. Вы можете нажать «Анализировать» или изменить текст вакансии справа."
    },
    "en": {
        # --- Лендинг и вход ---
        "hero_title": "Find out why your resume is being ignored",
        "hero_subtitle": "Over 75% of resumes are filtered out by ATS bots before a recruiter even sees them. Upload your resume and a job description — our AI will highlight weaknesses and rewrite it to help you land an interview.",
        "feat_1": "🎯 **Match Score:** find out your chance to pass the ATS filter (0-100%).",
        "feat_2": "🔑 **Keywords:** discover the skills the employer is looking for.",
        "feat_3": "📝 **Improved Resume:** AI rewrites your experience into an 'action → result' format.",
        "feat_4": "✉️ **Cover Letter:** a ready-to-use text tailored to the specific job.",
        "feat_5": "📥 **PDF Download:** get a clean file ready to be sent.",
        "login_form_title": "Login or Register",
        "login_form_info": "New users get 2 free analyses.",
        "email": "Your Email", "password": "Your Password",
        "btn_login": "Login / Register", "forgot_password": "Forgot password?",
        # --- Сброс пароля ---
        "reset_title": "🔑 Reset Password",
        "reset_step1": "Enter your registered email. We will send you a reset code.",
        "send_code": "Send Code", "code_sent": "Code sent! Check your email.",
        "reset_step2": "Enter the code from the email and your new password.",
        "code": "Code from email (6 digits)", "new_password": "New Password",
        "btn_reset": "Reset Password", "btn_back": "Back to Login",
        "reset_success": "Password changed successfully! You can now log in.",
        "reset_not_found": "User with this email not found.",
        "error_code": "Invalid or expired code.",
        "error_fill": "Please fill in all fields.",
        "error_pwd": "Incorrect password.", "success_reg": "Account created!",
        # --- Приложение ---
        "logout": "Log out", "logged_as": "Logged in as",
        "how_it_works": "**How it works:** upload resume → paste job description → choose tone → click «Analyze».",
        "left": "Free tries left", "upload": "1️⃣ Upload your resume (PDF, DOCX or TXT)",
        "job_desc": "2️⃣ Paste the job description", "tone": "3️⃣ Choose resume tone",
        "tone_options": ["Professional", "Creative", "Concise", "Achievement-oriented"],
        "btn_analyze": "🔍 Analyze", "warn_limit": "🚫 Free tries exhausted. Please subscribe to Pro below.",
        "spinner": "AI is reading... ~15 seconds", "err_upload": "Please upload a resume file first.",
        "err_job": "Please paste the job description.", "err_read": "Could not read text from the file.",
        "toast_ready": "✅ Analysis ready!", "ats_score": "**ATS Match Score:**",
        "btn_download_pdf": "📥 Download Resume as PDF", "btn_download_md": "💾 Download report (.md)", 
        "btn_copy": "📋 Click the icon on the right to copy",
        "pro_active": "✅ Your Pro subscription is active until", "pro_thanks": "Thank you for your support!",
        "want_more": "### 💎 Want more?", "pro_desc": "Subscribe to **Pro** — unlimited analyses.",
        "btn_buy": "Subscribe to Pro ($5/mo)", "feedback": "💬 Feedback",
        "try_example": "💡 Try with example data (no file upload needed)",
        "example_info": "Example IT resume loaded. You can click 'Analyze' or edit the job description."
    }
}

if 'lang' not in st.session_state:
    st.session_state.lang = "ru"
t = TEXTS[st.session_state.lang]

# Тестовые данные
EXAMPLE_RESUME_RU = """Иван Иванов
Python-разработчик (Middle)
Опыт работы:
- ООО "Ромашка" (2020-2023): Разработка бэкенда для e-commerce на Django. Увеличил скорость загрузки страниц на 40%.
- ИП Петров (2018-2020): Верстка сайтов HTML/CSS/JS.
Навыки: Python, Django, SQL, Git, Docker, HTML, CSS.
Образование: МГТУ им. Баумана, Прикладная математика и информатика."""
EXAMPLE_JOB_RU = """Ищем Python-разработчика.
Требования:
- Опыт коммерческой разработки на Python от 2 лет.
- Уверенное знание FastAPI.
- Опыт работы с базами данных PostgreSQL и Redis.
- Понимание принципов REST API.
- Опыт написания unit-тестов (pytest).
Будет плюсом: знание Docker и Kubernetes."""
EXAMPLE_RESUME_EN = """John Doe
Python Developer
Experience:
- E-commerce backend developer (2020-2023) using Django. Improved page load speed by 40%.
- Web developer (2018-2020) using HTML/CSS/JS.
Skills: Python, Django, SQL, Git, Docker, HTML, CSS.
Education: BS in Computer Science."""
EXAMPLE_JOB_EN = """We are looking for a Python Developer.
Requirements:
- 2+ years of commercial experience with Python.
- Strong knowledge of FastAPI.
- Experience with PostgreSQL and Redis.
- Understanding of REST API principles.
- Experience with unit testing (pytest).
Nice to have: Docker and Kubernetes."""

# =====================================================
# 2. УПРАВЛЕНИЕ СЕССИЕЙ (ЧЕРЕЗ URL)
# =====================================================
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email is None:
    url_email = st.query_params.get("user")
    if url_email:
        st.session_state.user_email = url_email
        st.rerun()

# =====================================================
# 3. ПОДКЛЮЧЕНИЕ К SUPABASE И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"DB Error: {e}")
    st.stop()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_reset_email(to_email, code):
    try:
        smtp_server = st.secrets["SMTP_SERVER"]
        smtp_port = int(st.secrets["SMTP_PORT"])
        sender_email = st.secrets["SMTP_EMAIL"]
        sender_password = st.secrets["SMTP_PASSWORD"]

        msg = MIMEText(f"Ваш код для сброса пароля в ResumeTailor AI: {code}\nКод действует 15 минут.\n\nЕсли вы не запрашивали сброс, просто проигнорируйте это письмо.")
        msg['Subject'] = "Сброс пароля ResumeTailor AI"
        msg['From'] = sender_email
        msg['To'] = to_email

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Ошибка отправки письма: {e}")
        return False

def extract_text(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        doc = Document(uploaded_file)
        text_parts = []
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)
        return "\n".join(text_parts)
    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    return ""

def generate_pdf(text):
    font_path = "DejaVuSans.ttf"
    if not os.path.exists(font_path):
        st.error("Ошибка: файл шрифта не найден в репозитории.")
        return b""
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", font_path)
    pdf.set_font("DejaVu", "", 12)
    clean_text = text.replace("##", "").replace("**", "").replace("###", "")
    pdf.multi_cell(0, 8, text=clean_text)
    return bytes(pdf.output())

# =====================================================
# 4. АВТОРИЗАЦИЯ И СБРОС ПАРОЛЯ (НОВЫЙ ЛЕНДИНГ)
# =====================================================
if not st.session_state.user_email:
    if 'reset_step' not in st.session_state:
        st.session_state.reset_step = 0

    if st.session_state.reset_step == 0:
        # Создаем две колонки: слева реклама, справа форма
        col_left, col_right = st.columns([1.3, 1], gap="large")
        
        with col_left:
            st.title("📄 ResumeTailor AI")
            st.markdown(f"### {t['hero_title']}")
            st.markdown(t['hero_subtitle'])
            st.write("") # Отступ
            st.markdown(t['feat_1'])
            st.markdown(t['feat_2'])
            st.markdown(t['feat_3'])
            st.markdown(t['feat_4'])
            st.markdown(t['feat_5'])
            
        with col_right:
            st.subheader(t["login_form_title"])
            st.info(t["login_form_info"])
            
            email_input = st.text_input(t["email"])
            password_input = st.text_input(t["password"], type="password")
            
            if st.button(t["btn_login"], type="primary", use_container_width=True):
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
                            st.query_params["user"] = email_input
                            st.rerun()
                        elif user['password'] == hashed_pwd:
                            st.session_state.user_email = email_input
                            st.query_params["user"] = email_input
                            st.rerun()
                        else:
                            st.error(t["error_pwd"])
                    else:
                        supabase.table('user_subscriptions').insert({'email': email_input, 'password': hashed_pwd, 'is_pro': False, 'free_uses': 0}).execute()
                        st.session_state.user_email = email_input
                        st.query_params["user"] = email_input
                        st.success(t["success_reg"])
                        st.rerun()
            
            if st.button(t["forgot_password"], use_container_width=True):
                st.session_state.reset_step = 1
                st.rerun()

    elif st.session_state.reset_step == 1:
        st.subheader(t["reset_title"])
        st.info(t["reset_step1"])
        
        reset_email = st.text_input(t["email"], key="reset_email")
        
        if st.button(t["send_code"], type="primary"):
            if not reset_email:
                st.error(t["error_fill"])
            else:
                res = supabase.table('user_subscriptions').select('email').eq('email', reset_email).execute()
                if len(res.data) > 0:
                    code = ''.join(random.choices(string.digits, k=6))
                    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                    
                    supabase.table('user_subscriptions').update({
                        'reset_code': code,
                        'reset_code_expires': expires
                    }).eq('email', reset_email).execute()
                    
                    if send_reset_email(reset_email, code):
                        st.success(t["code_sent"])
                        st.session_state.reset_step = 2
                        st.session_state.reset_email_val = reset_email
                        st.rerun()
                else:
                    st.error(t["reset_not_found"])
                    
        if st.button(t["btn_back"]):
            st.session_state.reset_step = 0
            st.rerun()

    elif st.session_state.reset_step == 2:
        st.subheader(t["reset_title"])
        st.info(t["reset_step2"])
        
        input_code = st.text_input(t["code"], max_chars=6)
        new_pwd = st.text_input(t["new_password"], type="password")
        
        if st.button(t["btn_reset"], type="primary"):
            if not input_code or not new_pwd:
                st.error(t["error_fill"])
            else:
                email = st.session_state.reset_email_val
                res = supabase.table('user_subscriptions').select('reset_code', 'reset_code_expires').eq('email', email).execute()
                
                if len(res.data) > 0:
                    user_data = res.data[0]
                    db_code = user_data.get('reset_code')
                    expires_str = user_data.get('reset_code_expires')
                    
                    if db_code == input_code and expires_str:
                        expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                        if expires > datetime.now(timezone.utc):
                            new_hash = hash_password(new_pwd)
                            supabase.table('user_subscriptions').update({
                                'password': new_hash,
                                'reset_code': None,
                                'reset_code_expires': None
                            }).eq('email', email).execute()
                            
                            st.success(t["reset_success"])
                            st.session_state.reset_step = 0
                            st.rerun()
                        else:
                            st.error(t["error_code"])
                    else:
                        st.error(t["error_code"])
        
        if st.button(t["btn_back"]):
            st.session_state.reset_step = 0
            st.rerun()
    # Политика конфиденциальности
    st.write("---")
    st.caption("🔒 Политика конфиденциальности: Мы используем ваш Email исключительно для входа в аккаунт. Мы не передаем ваши данные третьим лицам. Загруженные файлы резюме обрабатываются нейросетью и не сохраняются на наших серверах.")
    
    st.stop()

USER_EMAIL = st.session_state.user_email

# =====================================================
# 5. БОКОВАЯ ПАНЕЛЬ
# =====================================================
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
    st.link_button(t["feedback"], "https://vk.ru/s.belousov") 
    
    st.divider()
    if st.button(t["logout"], use_container_width=True):
        st.session_state.user_email = None
        st.query_params.clear()
        st.rerun()

# =====================================================
# 6. ПРОВЕРКА ПОДПИСКИ И ЛИМИТОВ (ИЗ БАЗЫ)
# =====================================================
response = supabase.table('user_subscriptions').select('is_pro', 'valid_until', 'free_uses').eq('email', USER_EMAIL).execute()
is_pro = False
sub_end_date = ""
free_uses = 0

if len(response.data) > 0:
    user_data = response.data[0]
    valid_until_str = user_data.get('valid_until')
    free_uses = user_data.get('free_uses', 0)
    
    if user_data.get('is_pro') and valid_until_str:
        valid_until = datetime.fromisoformat(valid_until_str.replace('Z', '+00:00'))
        if valid_until > datetime.now(timezone.utc):
            is_pro = True
            sub_end_date = valid_until.strftime("%d.%m.%Y")

# =====================================================
# 7. НЕЙРОСЕТЬ И ЛОГИКА АНАЛИЗА
# =====================================================
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except Exception:
    st.error("⚠️ API Key missing.")
    st.stop()

MODEL_NAME = "gemini-3.8-flash"

FREE_LIMIT = 2

if is_pro:
    disabled = False
    left_text = "∞ (Pro)"
else:
    left = max(FREE_LIMIT - free_uses, 0)
    disabled = left <= 0
    left_text = f"{left} / {FREE_LIMIT}"

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
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    if st.session_state.lang == "ru":
                        raise Exception("Серверы ИИ сейчас перегружены. Пожалуйста, нажмите «Анализировать» еще раз через 1-2 минуты.")
                    else:
                        raise Exception("AI servers are currently overloaded. Please click «Analyze» again in 1-2 minutes.")
            else:
                raise e

# =====================================================
# 8. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# =====================================================
st.title("📄 ResumeTailor AI")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(t["how_it_works"])
with col2:
    st.metric(t["left"], left_text)

st.divider()

use_example = st.checkbox(t["try_example"], value=False)

if use_example:
    st.info(t["example_info"])
    example_resume = EXAMPLE_RESUME_RU if st.session_state.lang == "ru" else EXAMPLE_RESUME_EN
    example_job = EXAMPLE_JOB_RU if st.session_state.lang == "ru" else EXAMPLE_JOB_EN
    
    uploaded = None
    job_text = st.text_area(t["job_desc"], value=example_job, height=200)
    resume_text = example_resume
else:
    uploaded = st.file_uploader(t["upload"], type=["pdf", "docx", "txt"])
    job_text = st.text_area(t["job_desc"], height=200)
    resume_text = None

tone_selection = st.selectbox(t["tone"], t["tone_options"])

if disabled:
    st.warning(t["warn_limit"])

if st.button(t["btn_analyze"], type="primary", disabled=disabled):
    if not use_example:
        if not uploaded:
            st.error(t["err_upload"])
            st.stop()
        else:
            resume_text = extract_text(uploaded)
            if not resume_text.strip():
                st.error(t["err_read"])
                st.stop()
            
    if not job_text.strip():
        st.error(t["err_job"])
        st.stop()
        
    with st.spinner(t["spinner"]):
        try:
            output_lang = "Russian" if st.session_state.lang == "ru" else "English"
            result = analyze(resume_text, job_text, output_lang, tone_selection)
            st.session_state.results = result
            
            if not is_pro:
                supabase.table('user_subscriptions').update({'free_uses': free_uses + 1}).eq('email', USER_EMAIL).execute()
                
            st.toast(t["toast_ready"])
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# =====================================================
# 9. РЕЗУЛЬТАТ
# =====================================================
if st.session_state.get("results"):
    st.divider()
    st.markdown(st.session_state.results)
    
    match = re.search(r"(\d{1,3})\s*%", st.session_state.results)
    if match:
        score = min(int(match.group(1)), 100)
        st.divider()
        st.markdown(f"{t['ats_score']} {score}%")
        st.progress(score / 100)
    
    col_pdf, col_md, col_empty = st.columns([1, 1, 1])
    
    with col_pdf:
        pdf_bytes = generate_pdf(st.session_state.results)
        st.download_button(
            label=t["btn_download_pdf"],
            data=pdf_bytes,
            file_name="improved_resume.pdf",
            mime="application/pdf",
            type="primary"
        )
        
    with col_md:
        st.download_button(
            label=t["btn_download_md"], 
            data=st.session_state.results, 
            file_name="resume_analysis.md", 
            mime="text/markdown"
        )
    
    st.markdown(t["btn_copy"])
    st.code(st.session_state.results, language="markdown")

# =====================================================
# 10. ОПЛАТА
# =====================================================
st.divider()
if is_pro:
    st.success(f"{t['pro_active']} **{sub_end_date}**. {t['pro_thanks']}")
else:
    st.markdown(t["want_more"])
    st.markdown(t["pro_desc"])
    payment_link = "https://app.lava.top/products/4eaedb98-cd63-44be-ac78-4f2525920fab"
    st.link_button(t["btn_buy"], url=payment_link, type="primary")
