import hashlib
import os
from datetime import datetime, timedelta
import time

import extra_streamlit_components as stx
import streamlit as st
from sqlalchemy import create_engine, text

# =========================================================
# DATABASE
# =========================================================

import os

# Usuwamy domyślny adres "db:5432", bo on działa tylko w Twoim Dockerze
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # To pomoże Ci w logach sprawdzić, czy Streamlit w ogóle widzi Twoje Secrets
    raise ValueError("BŁĄD: DATABASE_URL nie została znaleziona w Secrets!")

engine = create_engine(DATABASE_URL)

# =========================================================
# COOKIE MANAGER
# =========================================================

def get_cookie_manager():

    if "cookie_manager" not in st.session_state:

        st.session_state.cookie_manager = (
            stx.CookieManager()
        )

    return st.session_state.cookie_manager

# =========================================================
# DB INIT
# =========================================================

def init_auth_db():

    with engine.begin() as conn:

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                username TEXT,
                city TEXT,
                districts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                username TEXT REFERENCES users(username)
                ON DELETE CASCADE,
                achievement_name TEXT NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, achievement_name)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_stats (
                username TEXT PRIMARY KEY
                REFERENCES users(username)
                ON DELETE CASCADE,

                cities_viewed_count INTEGER DEFAULT 0,
                charts_generated_count INTEGER DEFAULT 0,
                valuation_requests_count INTEGER DEFAULT 0,

                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

# =========================================================
# PASSWORDS
# =========================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()

# =========================================================
# REGISTER
# =========================================================

def register_user(username, password):

    try:

        with engine.begin() as conn:

            conn.execute(
                text("""
                    INSERT INTO users
                    (username, password_hash)
                    VALUES (:u, :p)
                """),
                {
                    "u": username,
                    "p": hash_password(password)
                }
            )

            conn.execute(
                text("""
                    INSERT INTO user_stats(username)
                    VALUES (:u)
                    ON CONFLICT DO NOTHING
                """),
                {"u": username}
            )

        return True

    except Exception as e:

        print(e)
        return False

# =========================================================
# LOGIN
# =========================================================

def login_user(username, password):

    with engine.begin() as conn:

        result = conn.execute(
            text("""
                SELECT 1
                FROM users
                WHERE username=:u
                AND password_hash=:p
            """),
            {
                "u": username,
                "p": hash_password(password)
            }
        ).fetchone()

        return result is not None

# =========================================================
# LOGIN SESSION
# =========================================================

def login_session(username):

    cookie_manager = get_cookie_manager()

    expire_date = (
        datetime.utcnow()
        + timedelta(days=30)
    )

    cookie_manager.set(
        "real_estate_user",
        username,
        expires_at=expire_date
    )

    st.session_state.logged_in = True
    st.session_state.username = username

    # WAŻNE
    time.sleep(0.3)

    st.rerun()
# =========================================================
# LOGOUT
# =========================================================

def logout_session():

    cookie_manager = get_cookie_manager()

    cookie_manager.delete(
        "real_estate_user",
        key="delete_cookie"
    )

    keys = [
        "logged_in",
        "username",
        "auth_checked"
    ]

    for k in keys:

        if k in st.session_state:
            del st.session_state[k]

# =========================================================
# CHECK AUTH
# =========================================================

def check_auth():

    # aktywna sesja
    if st.session_state.get("logged_in"):
        return True

    cookie_manager = get_cookie_manager()

    # cookies jeszcze się ładują
    cookies = cookie_manager.get_all()

    if cookies is None:

        st.stop()

    saved_user = cookies.get(
        "real_estate_user"
    )

    # znaleziono cookie
    if saved_user:

        st.session_state.logged_in = True
        st.session_state.username = saved_user

        return True

    return False

# =========================================================
# SEARCH HISTORY
# =========================================================

def save_search(username, city, districts):

    with engine.begin() as conn:

        conn.execute(
            text("""
                INSERT INTO search_history
                (username, city, districts)
                VALUES (:u, :c, :d)
            """),
            {
                "u": username,
                "c": str(city),
                "d": str(districts)
            }
        )

def get_search_history(username):

    try:

        with engine.begin() as conn:

            result = conn.execute(
                text("""
                    SELECT
                        created_at,
                        city,
                        districts
                    FROM search_history
                    WHERE username=:u
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
                {"u": username}
            ).fetchall()

        return [
            {
                "Data":
                    r[0].strftime("%Y-%m-%d %H:%M"),
                "Miasta":
                    r[1],
                "Dzielnice":
                    r[2]
            }
            for r in result
        ]

    except:
        return []
    

def delete_user_offers(username):
    """Usuwa wszystkie oferty przypisane do danego użytkownika."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM offers WHERE username=:u"),
            {"u": username}
        )