import sys
import os
import time
import streamlit as st

# --- 1. SYSTEM PATH FIX ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --- 2. IMPORTY ---
from src.lang import get_text
from src.auth import (
    check_auth, init_auth_db, login_session, 
    login_user, logout_session, register_user
)

# --- 3. KONFIGURACJA STRONY (Musi być pierwsza!) ---
# Pobieramy tłumaczenia wstępnie dla tytułu karty przeglądarki
T_initial = get_text()
st.set_page_config(
    page_title=T_initial.get("page_title", "System Analizy Nieruchomości"),
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_login_screen(T):
    """Wyświetla formularze logowania i rejestracji."""
    st.title(T.get("login_title", "🔐 System Analizy Nieruchomości"))
    
    tab_login, tab_reg = st.tabs([
        T.get("login_btn", "Logowanie"), 
        T.get("reg_btn", "Rejestracja")
    ])

    with tab_login:
        u = st.text_input(T.get("login_user", "Użytkownik"), key="login_u")
        p = st.text_input(T.get("login_pass", "Hasło"), type="password", key="login_p")
        
        if st.button(T.get("login_btn", "Zaloguj"), use_container_width=True, key="btn_login"):
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
        
        if st.button(T.get("reg_btn", "Zarejestruj się"), use_container_width=True, key="btn_reg"):
            if register_user(nu, np):
                st.success("✅ Konto utworzone! Możesz się teraz zalogować.")
            else:
                st.error("❌ Użytkownik o tej nazwie już istnieje.")

def main():
    # Inicjalizacja bazy
    init_auth_db()
    # Sprawdzenie sesji
    check_auth()

    # 1. BRAMA BEZPIECZEŃSTWA
    if not st.session_state.get("logged_in"):
        # Czyścimy pozostałości nawigacji, jeśli jakimś cudem zostały
        render_login_screen(get_text())
        return # ABSOLUTNIE KOŃCZYMY WYKONYWANIE TUTAJ
    
    # 1. Wybór języka w sidebarze (widoczny zawsze)
    if "lang" not in st.session_state:
        st.session_state.lang = "PL"

    with st.sidebar:
        st.title("⚙️ Setup")
        selected_lang = st.radio(
            "Language",
            options=["PL", "EN"],
            index=0 if st.session_state.lang == "PL" else 1,
            key="lang_selector"
        )
        
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

    # Pobranie aktualnych tłumaczeń
    T = get_text()
    
    # --- KONFIGURACJA NAWIGACJI (Tylko dla zalogowanych) ---
    pages = {
        T.get("nav_group_general", "📊 Ogólne"): [
            st.Page("pages/dashboard.py", title=T.get("nav_dash", "Dashboard"), icon="🏠", default=True),
            st.Page("pages/comparision.py", title=T.get("nav_comp", "Porównywarka"), icon="⚖️"),
            st.Page("pages/ranking.py", title=T.get("nav_rank", "Ranking"), icon="🏆"),
        ],
        T.get("nav_group_ai", "🤖 AI & Analiza"): [
            st.Page("pages/analysis.py", title=T.get("nav_analysis", "Statystyki"), icon="📈"),
            st.Page("pages/MLvsAnalysis.py", title=T.get("nav_ml_vs", "Analiza vs ML"), icon="🔬"),
            st.Page("pages/predictionML.py", title=T.get("nav_predict", "Prognoza"), icon="🔮"),
        ],
        T.get("nav_group_tools", "🛠️ Narzędzia"): [
            st.Page("pages/scraper.py", title=T.get("nav_scraper", "Scraper"), icon="🕵️"),
        ]
    }

    # Inicjalizacja nawigacji
    pg = st.navigation(pages)

    # Sidebar dla zalogowanego użytkownika (pod menu stron)
    with st.sidebar:
        st.divider()
        st.success(f"👤 {st.session_state.get('username')}")
        if st.button(T.get("logout_btn", "Wyloguj"), use_container_width=True):
            logout_session()
            st.success("Wylogowywanie...") # Wizualne potwierdzenie dla użytkownika
            time.sleep(0.5) # Dajemy 500ms dla managera ciasteczek na usunięcie pliku
            st.rerun()

    # URUCHOMIENIE WYBRANEJ STRONY
    # To polecenie renderuje zawartość wybranego pliku z folderu pages/
    pg.run()

if __name__ == "__main__":
    main()