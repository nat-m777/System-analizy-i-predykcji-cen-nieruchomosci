import sys
import os
import time
import streamlit as st

# --- 1. KONFIGURACJA ŚCIEŻEK SYSTEMOWYCH ---
# Ustawienie BASE_DIR pozwala na bezproblemowe importy modułów z podkatalogów (np. src/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --- 2. IMPORTY MODUŁÓW WEWNĘTRZNYCH ---
from src.lang import get_text
from src.auth import (
    check_auth, init_auth_db, login_session, 
    login_user, logout_session, register_user
)

# --- 3. GLOBALNA KONFIGURACJA APLIKACJI ---
# st.set_page_config musi być wywołane przed jakimkolwiek innym elementem Streamlit
T_initial = get_text()
st.set_page_config(
    page_title=T_initial.get("page_title", "System Analizy Nieruchomości"),
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_login_screen(T):
    """
    Funkcja pomocnicza wyświetlająca interfejs logowania i rejestracji.
    
    Args:
        T (dict): Słownik przetłumaczonych fraz (i18n).
    """
    st.title(T.get("login_title", "🔐 System Analizy Nieruchomości"))
    
    # Podział ekranu na zakładki dla lepszej czytelności UI
    tab_login, tab_reg = st.tabs([
        T.get("login_btn", "Logowanie"), 
        T.get("reg_btn", "Rejestracja")
    ])

    with tab_login:
        u = st.text_input(T.get("login_user", "Użytkownik"), key="login_u")
        p = st.text_input(T.get("login_pass", "Hasło"), type="password", key="login_p")
        
        if st.button(T.get("login_btn", "Zaloguj"), use_container_width=True, key="btn_login"):
            # Proces autoryzacji użytkownika
            if login_user(u, p):
                login_session(u)
                st.success("Zalogowano pomyślnie!")
                time.sleep(0.5) # Krótka pauza, by użytkownik zauważył komunikat sukcesu
                st.rerun()
            else:
                st.error("❌ Błędne dane logowania")

    with tab_reg:
        nu = st.text_input(T.get("reg_user", "Nowy użytkownik"), key="reg_u")
        np = st.text_input(T.get("reg_pass", "Nowe hasło"), type="password", key="reg_p")
        
        if st.button(T.get("reg_btn", "Zarejestruj się"), use_container_width=True, key="btn_reg"):
            # Rejestracja nowego profilu w bazie danych
            if register_user(nu, np):
                st.success("✅ Konto utworzone! Możesz się teraz zalogować.")
            else:
                st.error("❌ Użytkownik o tej nazwie już istnieje.")

def main():
    """
    Główna funkcja sterująca przepływem aplikacji (Main Entry Point).
    Zarządza autoryzacją, językiem oraz nawigacją stron.
    """
    # Inicjalizacja komponentów bezpieczeństwa
    init_auth_db()
    check_auth()
    
    # Zarządzanie stanem języka w sesji użytkownika
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
        
        # Wykrywanie zmiany języka i natychmiastowe odświeżenie UI
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

    # Pobranie tekstów w aktualnie wybranym języku
    T = get_text()

    # BRAMA BEZPIECZEŃSTWA (Security Guard)
    # Jeśli flaga zalogowania nie jest ustawiona, renderujemy tylko login i przerywamy main()
    if not st.session_state.get("logged_in"):
        render_login_screen(get_text())
        return 
    
    # --- DEFINICJA STRON I NAWIGACJI ---
    # Struktura menu bocznego z podziałem na grupy tematyczne
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

    # Inicjalizacja systemowej nawigacji Streamlit
    pg = st.navigation(pages)

    # Elementy Sidebaru widoczne po zalogowaniu (Profil + Logout)
    with st.sidebar:
        st.divider()
        st.success(f"👤 {st.session_state.get('username')}")
        if st.button(T.get("logout_btn", "Wyloguj"), use_container_width=True):
            logout_session()
            st.success("Wylogowywanie...")
            time.sleep(0.5) 
            st.rerun()

    # Renderowanie zawartości aktywnej strony
    pg.run()

if __name__ == "__main__":
    main()