import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
import os
import streamlit as st

# Pobieramy URL z Twojego docker-compose
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:password@db:5432/real_estate")
engine = create_engine(DB_URL)

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
        # Zakładamy, że tabela nazywa się 'offers' i ma kolumnę 'owner'
        conn.execute(
            text("DELETE FROM offers WHERE owner = :u"),
            {"u": username}
        )
        conn.commit()
    

def check_auth():
    """Zwraca True jeśli użytkownik jest zalogowany, w przeciwnym razie False."""
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("Ta strona wymaga zalogowania.")
        st.info("Przejdź do strony głównej, aby się zalogować.")
        st.stop()  # Zatrzymuje renderowanie reszty strony