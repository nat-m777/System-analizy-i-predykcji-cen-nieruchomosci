import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
import os
import streamlit as st
import extra_streamlit_components as stx
import time

# --- KONFIGURACJA BAZY ---
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:password@db:5432/real_estate")
engine = create_engine(DB_URL)

# --- FUNKCJE BAZODANOWE ---

def init_auth_db():
    """Tworzy strukturę tabel, jeśli nie istnieją."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS offers (
                id SERIAL PRIMARY KEY,
                title TEXT, city TEXT, district TEXT,
                price DOUBLE PRECISION, area DOUBLE PRECISION,
                rooms INTEGER, price_per_m2 DOUBLE PRECISION,
                source TEXT, url TEXT, subdistrict TEXT,
                owner TEXT DEFAULT 'admin', username TEXT,
                scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                username TEXT, city TEXT, districts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                username TEXT REFERENCES users(username) ON DELETE CASCADE,
                achievement_name TEXT NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, achievement_name)
            );
            CREATE TABLE IF NOT EXISTS user_stats (
                username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                cities_viewed_count INTEGER DEFAULT 0,
                charts_generated_count INTEGER DEFAULT 0,
                valuation_requests_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            conn.execute(
                text("INSERT INTO user_stats (username) VALUES (:u) ON CONFLICT DO NOTHING"),
                {"u": username}
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

def delete_user_offers(username):
    """Usuwa ogłoszenia należące do danego użytkownika (używane w scraper.py)."""
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM offers WHERE username = :u"),
            {"u": username}
        )
        conn.commit()

def save_search(username, city, districts):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO search_history (username, city, districts) VALUES (:u, :c, :d)"),
            {"u": username, "c": str(city), "d": str(districts)}
        )
        conn.commit()

# --- MECHANIZM CIASTECZEK I AUTORYZACJI ---

def get_cookie_manager():
    """Zarządza instancją ciasteczek w sesji."""
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="global_cookie_manager")
    return st.session_state.cookie_manager

def check_auth():
    """
    Sprawdza autoryzację. 
    Umożliwia przetrwanie sesji po F5 dzięki ciasteczkom.
    """
    if st.session_state.get('logged_in'):
        return True

    cookie_manager = get_cookie_manager()
    
    # Czekamy na załadowanie ciasteczek z przeglądarki
    if 'cookies_initialized' not in st.session_state:
        time.sleep(0.7)
        st.session_state['cookies_initialized'] = True
        st.rerun()

    # Próba auto-loginu
    saved_user = cookie_manager.get('real_estate_user')
    if saved_user:
        st.session_state['logged_in'] = True
        st.session_state['username'] = saved_user
        st.rerun()

    # Jeśli brak sesji - wyświetlamy formularz logowania 'inline'
    st.title("🔑 Logowanie")
    st.warning("Ta strona wymaga zalogowania.")
    
    with st.form("auth_check_form"):
        u = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.form_submit_button("Zaloguj", use_container_width=True):
            if login_user(u, p):
                st.session_state['logged_in'] = True
                st.session_state['username'] = u
                cookie_manager.set('real_estate_user', u, max_age=31536000)
                st.success("Zalogowano!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Błędny login lub hasło")
    
    st.stop()