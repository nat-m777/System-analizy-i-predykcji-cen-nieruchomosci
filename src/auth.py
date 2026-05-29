import hashlib
import os
from datetime import datetime, timedelta
import time

import extra_streamlit_components as stx
import streamlit as st
from sqlalchemy import create_engine, text

# =========================================================
# KONFIGURACJA BAZY DANYCH (DATABASE)
# =========================================================

DATABASE_URL = None
try:
    if "DATABASE_URL" in st.secrets:
        DATABASE_URL = st.secrets["DATABASE_URL"]
except:
    pass

# 2. Jeśli go tam nie ma, poszukaj w zwykłych zmiennych środowiskowych (.env / Docker)
if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Jeśli nadal pusto – wyrzuć błąd
if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg2://admin:password@localhost:5432/real_estate"

# Inicjalizacja silnika SQLAlchemy - mostu między Pythonem a PostgreSQL
engine = create_engine(DATABASE_URL)

# =========================================================
# MENEDŻER CIASTECZEK (COOKIE MANAGER)
# =========================================================

def get_cookie_manager():
    """
    Inicjalizuje komponent stx.CookieManager, który pozwala na trwałe 
    przechowywanie sesji w przeglądarce użytkownika (Persistence).
    """
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager

# =========================================================
# INICJALIZACJA STRUKTURY (DB INIT)
# =========================================================

def init_auth_db():
    """
    Tworzy niezbędne tabele systemowe, jeśli nie istnieją. 
    Obsługuje użytkowników, historię wyszukiwań, osiągnięcia oraz statystyki.
    """
    with engine.begin() as conn:
        # Tabela użytkowników - przechowuje loginy i zahashowane hasła
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
        """))

        # Historia filtrów - pozwala użytkownikowi wrócić do poprzednich analiz
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                username TEXT,
                city TEXT,
                districts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Osiągnięcia (Gamification) - powiązane relacją klucza obcego z tabelą users
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                username TEXT REFERENCES users(username) ON DELETE CASCADE,
                achievement_name TEXT NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, achievement_name)
            );
        """))

        # Liczniki aktywności - niezbędne do sprawdzania warunków odblokowania medali
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_stats (
                username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                cities_viewed_count INTEGER DEFAULT 0,
                charts_generated_count INTEGER DEFAULT 0,
                valuation_requests_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

# =========================================================
# SZYFROWANIE HASEŁ (PASSWORDS)
# =========================================================

def hash_password(password):
    """
    Zmienia hasło w formie tekstowej na bezpieczny ciąg SHA-256. 
    Nigdy nie przechowujemy haseł w czystym tekście!
    """
    return hashlib.sha256(password.encode()).hexdigest()

# =========================================================
# REJESTRACJA (REGISTER)
# =========================================================

def register_user(username, password):
    """
    Dodaje nowego użytkownika do bazy oraz tworzy dla niego pusty rekord statystyk.
    """
    try:
        with engine.begin() as conn:
            # Wstawienie użytkownika z zahashowanym hasłem
            conn.execute(
                text("INSERT INTO users (username, password_hash) VALUES (:u, :p)"),
                {"u": username, "p": hash_password(password)}
            )
            # Inicjalizacja statystyk (0 wizyt, 0 wycen itd.)
            conn.execute(
                text("INSERT INTO user_stats(username) VALUES (:u) ON CONFLICT DO NOTHING"),
                {"u": username}
            )
        return True
    except Exception as e:
        print(f"Błąd rejestracji: {e}")
        return False

# =========================================================
# LOGOWANIE (LOGIN)
# =========================================================

def login_user(username, password):
    """
    Sprawdza, czy w bazie istnieje para użytkownik + hash(hasło).
    """
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT 1 FROM users WHERE username=:u AND password_hash=:p"),
            {"u": username, "p": hash_password(password)}
        ).fetchone()
        return result is not None

# =========================================================
# ZARZĄDZANIE SESJĄ (LOGIN SESSION)
# =========================================================

def login_session(username):
    """
    Ustawia ciasteczko w przeglądarce (na 30 dni) i inicjuje sesję Streamlit.
    """
    cookie_manager = get_cookie_manager()
    expire_date = datetime.utcnow() + timedelta(days=30)

    # Zapisanie loginu do ciasteczka, aby użytkownik nie musiał się logować przy każdym odświeżeniu
    cookie_manager.set("real_estate_user", username, expires_at=expire_date)

    st.session_state.logged_in = True
    st.session_state.username = username

    # Krótka pauza, aby komponent ciasteczek zdążył przetworzyć dane przed odświeżeniem
    time.sleep(0.3)
    st.rerun()

# =========================================================
# WYLOGOWANIE (LOGOUT)
# =========================================================

def logout_session():
    """
    Usuwa ciasteczko z przeglądarki i całkowicie czyści pamięć podręczną sesji.
    """
    cookie_manager = get_cookie_manager()
    cookie_manager.delete("real_estate_user", key="delete_cookie")

    # Czyszczenie wszystkich kluczy w st.session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Ustawienie stanów domyślnych po wylogowaniu
    st.session_state["logged_in"] = False
    st.session_state["auth_checked"] = True

# =========================================================
# WERYFIKACJA AUTORYZACJI (CHECK AUTH)
# =========================================================

def check_auth():
    """
    Kluczowa funkcja sprawdzająca, czy użytkownik ma dostęp do strony. 
    Najpierw sprawdza stan sesji, potem zagląda do ciasteczek przeglądarki.
    """
    # Szybka ścieżka: użytkownik jest już zalogowany w tej sesji
    if st.session_state.get("logged_in"):
        return True

    cookie_manager = get_cookie_manager()
    cookies = cookie_manager.get_all()

    # Jeśli komponent ciasteczek jeszcze nie odpowiedział, wstrzymujemy renderowanie
    if cookies is None:
        st.stop()

    saved_user = cookies.get("real_estate_user")

    # Jeśli znaleziono ważne ciasteczko, automatycznie logujemy użytkownika
    if saved_user:
        st.session_state.logged_in = True
        st.session_state.username = saved_user
        return True

    return False

# =========================================================
# HISTORIA WYSZUKIWANIA (SEARCH HISTORY)
# =========================================================

def save_search(username, city, districts):
    """Zapisuje użyte filtry do bazy danych."""
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO search_history (username, city, districts) VALUES (:u, :c, :d)"),
            {"u": username, "c": str(city), "d": str(districts)}
        )

def get_search_history(username):
    """Pobiera 20 ostatnich wyszukiwań danego użytkownika."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT created_at, city, districts 
                    FROM search_history 
                    WHERE username=:u 
                    ORDER BY created_at DESC 
                    LIMIT 20
                """),
                {"u": username}
            ).fetchall()

        return [
            {
                "Data": r[0].strftime("%Y-%m-%d %H:%M"),
                "Miasta": r[1],
                "Dzielnice": r[2]
            }
            for r in result
        ]
    except:
        return []

def delete_user_offers(username):
    """Usuwa wszystkie oferty pobrane przez danego użytkownika z tabeli offers."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM offers WHERE username=:u"),
            {"u": username}
        )