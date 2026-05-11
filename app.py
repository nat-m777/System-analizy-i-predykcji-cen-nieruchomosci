import streamlit as st
from src.auth import login_user, register_user, init_auth_db, get_cookie_manager
import time

# 1. Konfiguracja musi być na samym początku (przed jakimkolwiek kodem st.)
st.set_page_config(page_title="System Analizy", initial_sidebar_state="collapsed")

# Inicjalizacja sesji języka
if 'lang' not in st.session_state:
    st.session_state.lang = "PL"

# Selektor języka
st.sidebar.radio("Language / Język", options=["PL", "EN"], key="lang_selector", 
                 on_change=lambda: st.session_state.update({"lang": st.session_state.lang_selector}))

def main():
    init_auth_db()
    cookie_manager = get_cookie_manager()

    # --- KLUCZ DO PRZETRWANIA F5 ---
    # 2. Mechanizm oczekiwania i auto-logowania
    if not st.session_state.get('logged_in'):
        # Dajemy czas komponentowi na załadowanie ciasteczek z przeglądarki
        if 'cookies_initialized' not in st.session_state:
            time.sleep(0.8) # Nieco dłuższy czas dla pewności przy F5
            st.session_state['cookies_initialized'] = True
            st.rerun()

        # Pobieramy ciasteczko
        saved_user = cookie_manager.get('real_estate_user')
        
        # Jeśli ciasteczko istnieje, przywracamy sesję
        if saved_user:
            st.session_state['logged_in'] = True
            st.session_state['username'] = saved_user
            st.rerun()

    # --- EKRAN LOGOWANIA (Tylko jeśli auto-login się nie udał) ---
    if not st.session_state.get('logged_in'):
        st.title("🔐 System Analizy Nieruchomości")
        
        tab_l, tab_r = st.tabs(["Logowanie", "Rejestracja"])
        
        with tab_l:
            u = st.text_input("Login", key="login_u")
            p = st.text_input("Hasło", type="password", key="login_p")
            if st.button("Zaloguj", use_container_width=True):
                if login_user(u, p):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    
                    # ZAPIS CIASTECZKA: Musi mieć ustawione max_age, by przetrwało zamknięcie przeglądarki/F5
                    cookie_manager.set('real_estate_user', u, max_age=31536000) # 1 rok
                    
                    st.success("Zalogowano pomyślnie!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Błędny login lub hasło")

        with tab_r:
            nu = st.text_input("Nowy Login", key="reg_u")
            np = st.text_input("Nowe Hasło", type="password", key="reg_p")
            if st.button("Utwórz konto", use_container_width=True):
                if register_user(nu, np):
                    st.success("Konto utworzone! Możesz się zalogować.")
                else:
                    st.error("Użytkownik już istnieje lub błąd bazy.")
        
        st.stop() 

    # --- WIDOK DLA ZALOGOWANYCH ---
    st.sidebar.success(f"Zalogowano jako: {st.session_state['username']}")
    st.title(f"Witaj {st.session_state['username']}! 👋")
    st.info("Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę.")
    
    if st.sidebar.button("Wyloguj"):
        cookie_manager.delete('real_estate_user')
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('cookies_initialized', None)
        st.rerun()

if __name__ == "__main__":
    main()