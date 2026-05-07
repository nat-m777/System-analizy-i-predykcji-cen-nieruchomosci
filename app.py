import streamlit as st
from src.auth import login_user, register_user, init_auth_db, get_cookie_manager
import time

# 1. Konfiguracja musi być na samym początku
st.set_page_config(page_title="System Analizy", initial_sidebar_state="collapsed")

def main():
    # Inicjalizacja bazy użytkowników
    init_auth_db()

    # Pobieramy menedżera ciasteczek (używamy wspólnej funkcji z src/auth.py)
    cookie_manager = get_cookie_manager()

    # 2. Mechanizm oczekiwania na załadowanie ciasteczek z przeglądarki
    if 'cookies_initialized' not in st.session_state:
        # Dajemy komponentowi czas na komunikację z przeglądarką
        time.sleep(0.6) 
        st.session_state['cookies_initialized'] = True
        st.rerun()

    # 3. Próba automatycznego logowania z ciasteczka
    saved_user = cookie_manager.get('real_estate_user')
    
    if saved_user and not st.session_state.get('logged_in'):
        st.session_state['logged_in'] = True
        st.session_state['username'] = saved_user
        # Po automatycznym zalogowaniu odświeżamy, by pokazać menu
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
                    
                    # ZAPIS CIASTECZKA: Kluczowe dla przetrwania F5
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
        
        # Blokada – niezalogowany nie widzi nic poniżej
        st.stop() 

    # --- WIDOK DLA ZALOGOWANYCH ---
    # Przywracamy pasek boczny dla zalogowanych (opcjonalnie przez CSS lub po prostu st.sidebar)
    st.sidebar.success(f"Zalogowano jako: {st.session_state['username']}")
    st.title(f"Witaj {st.session_state['username']}! 👋")
    st.info("Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę.")
    
    # Przycisk wylogowania musi czyścić i sesję, i ciasteczko
    if st.sidebar.button("Wyloguj"):
        cookie_manager.delete('real_estate_user')
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        # Czyścimy też flagę inicjalizacji, by przy ponownym logowaniu znów poczekał na ciastka
        st.session_state.pop('cookies_initialized', None)
        st.rerun()

if __name__ == "__main__":
    main()