import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
import os
import streamlit as st
import extra_streamlit_components as stx
import time

# --- BAZA ---
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:password@db:5432/real_estate"
)

engine = create_engine(DB_URL)


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
            CREATE TABLE IF NOT EXISTS offers (
                id SERIAL PRIMARY KEY,
                title TEXT,
                city TEXT,
                district TEXT,
                price DOUBLE PRECISION,
                area DOUBLE PRECISION,
                rooms INTEGER,
                price_per_m2 DOUBLE PRECISION,
                source TEXT,
                url TEXT,
                subdistrict TEXT,
                owner TEXT DEFAULT 'admin',
                username TEXT,
                scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    return hashlib.sha256(password.encode()).hexdigest()


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
                    INSERT INTO user_stats (username)
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
                SELECT *
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


# =========================================================
# DELETE OFFERS
# =========================================================

def delete_user_offers(username):

    with engine.begin() as conn:

        conn.execute(
            text("""
                DELETE FROM offers
                WHERE username=:u
            """),
            {"u": username}
        )


# =========================================================
# LOGIN SESSION
# =========================================================

def login_session(username):

    cookie_manager = get_cookie_manager()

    st.session_state["logged_in"] = True
    st.session_state["username"] = username

    # cookie na 30 dni
    cookie_manager.set(
        "real_estate_user",
        username,
        expires_at=time.time() + 60 * 60 * 24 * 30
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_session():

    cookie_manager = get_cookie_manager()

    cookie_manager.delete("real_estate_user")

    keys = [
        "logged_in",
        "username"
    ]

    for k in keys:
        if k in st.session_state:
            del st.session_state[k]

    st.rerun()


# =========================================================
# CHECK AUTH
# =========================================================

def check_auth():

    cookie_manager = get_cookie_manager()

    # już zalogowany
    if st.session_state.get("logged_in"):
        return True

    # ma cookie
    saved_user = cookie_manager.get("real_estate_user")

    if saved_user:

        st.session_state["logged_in"] = True
        st.session_state["username"] = saved_user

        return True

    return False