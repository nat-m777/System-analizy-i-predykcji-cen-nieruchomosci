# src/utils.py
import streamlit as st
import pandas as pd
from src.database.db_manager import DBManager
import base64
from io import BytesIO

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

def get_table_download_link_csv(df):
    """Generuje link do pobrania danych w formacie CSV."""
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="analiza_rynku.csv" style="text-decoration:none;"><button style="background-color:#4CAF50; border:none; color:white; padding:10px 20px; border-radius:5px; cursor:pointer;">📥 Pobierz CSV</button></a>'

def generate_pdf_report(df, username):
    """Prosta generacja raportu tekstowego PDF (symulacja przez BytesIO)."""
    # Dla pełnego PDF z tabelami zaleca się bibliotekę fpdf
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(40, 10, f"Raport Analizy Rynku - Uzytkownik: {username}")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, f"Liczba analizowanych ofert: {len(df)}")
    pdf.ln(10)
    
    # Przykładowe statystyki
    avg_price = df['price_per_m2'].mean()
    pdf.cell(40, 10, f"Srednia cena za m2: {round(avg_price, 2)} PLN")
    pdf.ln(20)
    
    # Nagłówki tabeli (uproszczone)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, "Miasto", 1)
    pdf.cell(60, 10, "Dzielnica", 1)
    pdf.cell(40, 10, "Cena/m2", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    for i in range(min(len(df), 20)):  # Top 20 ofert
        pdf.cell(60, 10, str(df.iloc[i]['city']), 1)
        pdf.cell(60, 10, str(df.iloc[i].get('district', 'N/A')), 1)
        pdf.cell(40, 10, f"{df.iloc[i]['price_per_m2']:.0f}", 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')
