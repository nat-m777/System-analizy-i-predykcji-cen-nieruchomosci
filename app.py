import sys
import os
import time
from datetime import datetime
from io import BytesIO

# =========================================================
# SYSTEM PATH FIX (Musi być przed jakimkolwiek importem z src)
# =========================================================
# Pobieramy absolutną ścieżkę do folderu, w którym jest app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="System Analizy Nieruchomości",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# TRY-IMPORT BLOCK (Z diagnostyką błędów)
# =========================================================
try:
    import pandas as pd
    from fpdf import FPDF
    
    # Importy własne z pełną ścieżką
    from src.utils import get_db, clean_df
    from src.analysis.charts import show_price_prediction_logic
    from src.i18n import LANGUAGES
    from src.auth import (
        check_auth,
        init_auth_db,
        login_session,
        login_user,
        logout_session,
        register_user
    )
    import src.lang as lang_module
    get_text = lang_module.get_text

except ModuleNotFoundError as e:
    st.error(f"❌ Błąd struktury plików: {e}")
    st.write("### Diagnostyka ścieżek:")
    st.code(f"Katalog główny: {BASE_DIR}")
    if os.path.exists(os.path.join(BASE_DIR, "src")):
        st.write("✅ Folder 'src' istnieje.")
        st.write(f"Zawartość 'src': {os.listdir(os.path.join(BASE_DIR, 'src'))}")
    else:
        st.error("❌ Folder 'src' NIE istnieje w katalogu głównym!")
    st.stop()

# =========================================================
# INICJALIZACJA SYSTEMU
# =========================================================
init_auth_db()

# Zarządzanie językiem
if "lang" not in st.session_state:
    st.session_state.lang = "PL"

# Pobranie tekstów (T to skrót od Translations)
T = get_text()

# =========================================================
# SIDEBAR (Język i Status)
# =========================================================
with st.sidebar:
    selected_lang = st.radio(
        "🌍 Język / Language",
        options=["PL", "EN"],
        index=0 if st.session_state.lang == "PL" else 1,
        key="lang_selector"
    )
    
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.rerun()

# =========================================================
# PROCES LOGOWANIA (CIASTECZKA + SESJA)
# =========================================================
# check_auth() zajmie się odczytem ciasteczka po F5
is_logged_in = check_auth()

if not st.session_state.get("logged_in"):
    st.title(T.get("login_title", "🔐 System Analizy Nieruchomości"))
    
    tab_login, tab_reg = st.tabs([
        T.get("login_btn", "Logowanie"), 
        T.get("reg_btn", "Rejestracja")
    ])

    with tab_login:
        u = st.text_input(T.get("login_user", "Użytkownik"), key="login_u")
        p = st.text_input(T.get("login_pass", "Hasło"), type="password", key="login_p")
        
        if st.button(T.get("login_btn", "Zaloguj"), use_container_width=True):
            if login_user(u, p):
                login_session(u)
                st.success("Zalogowano pomyślnie!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Błędne dane logowania")

    with tab_reg:
        nu = st.text_input(T.get("reg_user", "Nowy użytkownik"), key="reg_u")
        np = st.text_input(T.get("reg_pass", "Nowe hasło"), type="password", key="reg_p")
        
        if st.button(T.get("reg_btn", "Zarejestruj się"), use_container_width=True):
            if register_user(nu, np):
                st.success("✅ Konto utworzone! Możesz się teraz zalogować.")
            else:
                st.error("❌ Użytkownik o tej nazwie już istnieje.")
    
    st.stop()

# =========================================================
# GŁÓWNY PULPIT (Dla zalogowanych)
# =========================================================
st.sidebar.divider()
st.sidebar.success(f"👤 {st.session_state.username}")

if st.sidebar.button(T.get("logout_btn", "Wyloguj"), use_container_width=True):
    logout_session()

st.title(f"Witaj {st.session_state.username}! 👋")
st.info(T.get("welcome_msg", "Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę."))

# Przykładowe podsumowanie (jeśli masz db)
try:
    db = get_db()
    stats = db.get_user_stats(st.session_state.username)
    if stats:
        c1, c2, c3 = st.columns(3)
        c1.metric("Wyszukiwania", stats.get('cities_viewed_count', 0))
        c2.metric("Wyceny", stats.get('valuation_requests_count', 0))
        c3.metric("Wykresy", stats.get('charts_generated_count', 0))
except:
    pass