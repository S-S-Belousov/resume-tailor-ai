import re
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
from supabase import create_client, Client

st.set_page_config(page_title="ResumeTailor AI", page_icon="📄", layout="centered")

# ---------- 1. ПОДКЛЮЧЕНИЕ К SUPABASE ----------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Ошибка подключения к базе данных: {e}")
    st.stop()

# ---------- 2. АВТОРИЗАЦИЯ ПО EMAIL ----------
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
    email_input = st.text_input("Введите ваш Email для входа")
    if st.button("Войти"):
        if email_input:
            st.session_state.user_email = email_input
            st.rerun()
    st.stop()

USER_EMAIL = st.session_state.user_email

# ---------- 3. ПРОВЕРКА СТАТУСА PRO ----------
response = supabase.table('user_subscriptions').select('is_pro').eq('email', USER_EMAIL).execute()
is_pro = len(response.data) > 0 and response.data[0]['is_pro']

# ---------- 4. ПОДКЛЮЧЕНИЕ НЕЙРОСЕТИ ----------
# ... (код без изменений)
