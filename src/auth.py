import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
import os
import streamlit as st
import extra_streamlit_components as stx
import time

# Pobieramy URL z Twojego docker-compose
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:password@db:5432/real_estate")
engine = create_engine(DB_URL)

# --- FUNKCJE POMOCNICZE I BAZA ---

def init_auth_db():
    """Tworzy tabele użytkowników i historii, jeśli nie istnieją."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                username TEXT REFERENCES users(username),
                city TEXT,
                districts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash) VALUES (:u, :p)"),
                {"u": username, "p": hash_password(password)}
            )
            conn.commit()
            return True
    except:
        return False

def login_user(username, password):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE username = :u AND password_hash = :p"),
            {"u": username, "p": hash_password(password)}
        ).fetchone()
        return result is not None

# --- HISTORIA I ZARZĄDZANIE DANYMI ---

def save_search(username, city, districts):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO search_history (username, city, districts) VALUES (:u, :c, :d)"),
            {"u": username, "c": str(city), "d": str(districts)}
        )
        conn.commit()

def get_search_history(username):
    with engine.connect() as conn:
        query = text("SELECT city, districts, created_at FROM search_history WHERE username = :u ORDER BY created_at DESC")
        df = pd.read_sql(query, conn, params={"u": username})
        return df

def delete_user_offers(username):
    """Usuwa ogłoszenia należące TYLKO do danego użytkownika."""
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM offers WHERE owner = :u"),
            {"u": username}
        )
        conn.commit()

# --- NOWA LOGIKA AUTORYZACJI Z CIASTECZKAMI ---

def get_cookie_manager():
    """Inicjalizuje menedżera ciasteczek."""
    return stx.CookieManager()

def check_auth():
    """
    Zabezpiecza stronę. Sprawdza session_state, a jeśli jest pusty (po F5), 
    próbuje odczytać ciasteczko z przeglądarki.
    """
    cookie_manager = get_cookie_manager()
    
    # 1. Streamlit potrzebuje chwili na pobranie ciasteczek przy pierwszym renderowaniu
    if 'cookies_initialized' not in st.session_state:
        time.sleep(0.6)  # Kluczowe opóźnienie dla stabilności
        st.session_state['cookies_initialized'] = True
        st.rerun()

    # 2. Jeśli nie jesteśmy zalogowani w tej sesji, sprawdźmy ciasteczka
    if not st.session_state.get('logged_in'):
        saved_user = cookie_manager.get('real_estate_user')
        if saved_user:
            st.session_state['logged_in'] = True
            st.session_state['username'] = saved_user
            st.rerun()

    # 3. Jeśli po sprawdzeniu ciasteczek nadal brak zalogowania -> blokujemy
    if not st.session_state.get('logged_in'):
        st.warning("🔒 Ta strona wymaga zalogowania.")
        st.info("Przejdź do strony głównej (Logowanie), aby uzyskać dostęp.")
        st.stop()
    
    return True