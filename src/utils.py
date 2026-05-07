# src/utils.py
import streamlit as st
import pandas as pd
from src.database.db_manager import DBManager

def get_db():
    db = DBManager()
    db.create_tables()
    return db

# src/utils.py

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # --- INTELIGENTNE WYKRYWANIE DZIELNICY ---
    # Szukamy kolumny 'district' lub 'subdistrict'
    if "district" in df.columns:
        # Jeśli district już jest, upewniamy się, że nie ma duplikatu subdistrict
        if "subdistrict" in df.columns:
            df = df.drop(columns=["subdistrict"])
    elif "subdistrict" in df.columns:
        # Jeśli jest tylko subdistrict, zmieniamy nazwę na district
        df = df.rename(columns={"subdistrict": "district"})
    else:
        # Jeśli nie ma żadnej, tworzymy ją, żeby dashboard nie wyrzucał błędu
        df["district"] = "Nieznana"

    # --- CZYSZCZENIE I FORMATOWANIE ---
    df["city"] = df["city"].astype(str).str.strip().str.capitalize()
    
    # Zamieniamy puste wartości w dzielnicy na czytelny tekst
    df["district"] = df["district"].fillna("Nieznana").astype(str).replace(["None", "nan", ""], "Nieznana")

    # Konwersja typów numerycznych
    for col in ["price", "area", "price_per_m2", "rooms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Zwracamy tylko sensowne oferty
    return df[df["price"].notna() & df["area"].notna()]

def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

