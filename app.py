import streamlit as st
import extra_streamlit_components as stx
from src.auth import login_user, register_user, init_auth_db
import time

# Konfiguracja strony musi być na samym początku
st.set_page_config(page_title="System Analizy", initial_sidebar_state="collapsed")

def main():
    init_auth_db()

    # Inicjalizacja menedżera ciasteczek
    cookie_manager = stx.CookieManager()

    # WAŻNE: Krótka pauza, aby ciasteczka zdążyły się załadować z przeglądarki
    # Streamlit musi wyrenderować komponent, zanim odczyta dane
    if 'cookies_ready' not in st.session_state:
        time.sleep(0.5) 
        st.session_state['cookies_ready'] = True
        st.rerun()

    # 1. Próba odczytu ciasteczka
    saved_user = cookie_manager.get('real_estate_user')

    # 2. Logika sesji
    if saved_user and not st.session_state.get('logged_in'):
        st.session_state['logged_in'] = True
        st.session_state['username'] = saved_user
        st.rerun()

    # --- EKRAN LOGOWANIA ---
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
                    # Zapisujemy ciasteczko na rok (w sekundach)
                    cookie_manager.set('real_estate_user', u, max_age=31536000)
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
        
        st.stop() # Blokada dla niezalogowanych

    # --- WIDOK DLA ZALOGOWANYCH ---
    st.sidebar.success(f"Zalogowano jako: {st.session_state['username']}")
    st.title(f"Witaj {st.session_state['username']}! 👋")
    st.info("Wybierz moduł z menu po lewej stronie, aby rozpocząć analizę.")
    
    if st.sidebar.button("Wyloguj"):
        cookie_manager.delete('real_estate_user')
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.rerun()

if __name__ == "__main__":
    main()