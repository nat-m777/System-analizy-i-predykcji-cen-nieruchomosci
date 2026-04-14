"""
Główny moduł aplikacji Streamlit: Analiza Nieruchomości Pro.
Zarządza interfejsem użytkownika, nawigacją oraz integracją z bazą danych i scraperem.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.database.db_manager import DBManager
from src.scraper.otodom import OtodomScraper
from src.analysis.charts import (
    create_price_histogram,
    create_area_vs_price_chart,
    show_price_prediction_logic
)

# --- FUNKCJE POMOCNICZE ---

def local_css(file_name):
    """Ładuje niestandardowy arkusz stylów CSS."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Czyści i formatuje dane z bazy danych.
    Usuwa niekompletne oferty i ujednolica nazewnictwo.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["city"] = df["city"].astype(str).str.strip().str.capitalize()
    df["district"] = df["district"].astype(str).replace(["None", "nan", ""], pd.NA)

    for col in ["price", "area", "price_per_m2", "rooms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[df["price"].notna() & df["area"].notna()]

# --- WIDOKI (STRONY) ---

def show_dashboard(db):
    """Wyświetla stronę główną z metrykami i wykresami."""
    st.title("📊 Przegląd Rynku")
    df_raw = db.get_all_offers()
    df = clean_df(df_raw)

    if df.empty:
        st.info("Baza danych jest pusta. Pobierz dane w zakładce Scraper.")
        return

    # Filtry w sidebarze
    st.sidebar.subheader("Filtry")
    selected_cities = st.sidebar.multiselect(
        "Wybierz Miasta", options=sorted(df["city"].unique()), default=list(df["city"].unique())
    )
    
    df_filtered = df[df["city"].isin(selected_cities)]

    # Metryki
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Liczba ofert", len(df_filtered))
    c2.metric("Śr. cena", f"{round(df_filtered['price'].mean()/1000, 1)} tys. zł")
    c3.metric("Śr. metraż", f"{round(df_filtered['area'].mean(), 1)} m²")
    c4.metric("Cena/m²", f"{round(df_filtered['price_per_m2'].mean(), 0)} zł")

    # Wykresy w zakładkach
    t1, t2 = st.tabs(["📊 Rozkład cen", "📈 Cena vs Metraż"])
    with t1:
        st.plotly_chart(create_price_histogram(df_filtered), use_container_width=True)
    with t2:
        st.plotly_chart(create_area_vs_price_chart(df_filtered), use_container_width=True)

    st.subheader("Ostatnio pobrane oferty")
    st.dataframe(df_filtered.sort_values("scrape_date", ascending=False), use_container_width=True)

def show_scraper_page(db):
    """Interfejs do sterowania scraperem Otodom."""
    st.title("🕵️ Pobieranie nowych danych")
    
    city_config = {
        "Warszawa": ["bemowo", "bialoleka", "bielany", "mokotow", "srodmiescie", "wola"],
        "Krakow": ["stare-miasto", "krowodrza", "podgorze"],
        "Wroclaw": ["krzyki", "fabryczna", "stare-miasto"]
    }

    city = st.selectbox("Wybierz miasto", list(city_config.keys()))
    selected_districts = st.multiselect("Dzielnice", options=city_config[city], default=city_config[city][:2])
    max_pages = st.slider("Stron do pobrania", 1, 15, 2)

    if st.button("Uruchom Scraper"):
        scraper = OtodomScraper()
        with st.spinner(f"Pobieranie danych dla miasta {city}..."):
            try:
                df = scraper.fetch_data(city, max_pages=max_pages, selected_districts=selected_districts)
                df = clean_df(df)
                if not df.empty:
                    db.insert_offers(df)
                    st.success(f"Sukces! Dodano {len(df)} nowych ofert.")
                    st.dataframe(df.head())
                else:
                    st.warning("Nie znaleziono nowych ofert.")
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")

def show_analysis_page(db):
    """Strona z zaawansowaną statystyką i symulacją cen."""
    st.title("📈 Analiza Statystyczna")
    df = clean_df(db.get_all_offers())

    if df.empty:
        st.warning("Brak danych do analizy.")
        return

    st.subheader("💡 Kalkulator szacunkowej ceny")
    with st.form("calc_form"):
        col1, col2 = st.columns(2)
        with col1:
            in_area = st.number_input("Metraż (m²)", 10, 200, 50)
            in_city = st.selectbox("Miasto", sorted(df["city"].unique()))
        with col2:
            in_rooms = st.slider("Liczba pokoi", 1, 6, 2)
            districts = df[df["city"] == in_city]["district"].dropna().unique()
            in_dist = st.selectbox("Dzielnica", sorted(districts))
        
        if st.form_submit_button("Oblicz estymację"):
            show_price_prediction_logic(df, in_area, in_city, in_dist)

# --- MAIN ---

def main():
    """Główna funkcja sterująca aplikacją."""
    # Załaduj style
    local_css("assets/style.css")

    # Inicjalizacja bazy danych
    db = DBManager()
    db.create_tables()

    # Sidebar - Nawigacja
    st.sidebar.header("🏠 Real Estate App")
    menu = {
        "📊 Dashboard": show_dashboard,
        "🕵️ Pobieranie Danych": show_scraper_page,
        "📈 Analiza Statystyczna": show_analysis_page,
        "🤖 ML": lambda db: st.title("Model ML wkrótce..."),
    }
    
    choice = st.sidebar.radio("Menu", list(menu.keys()))

    # Uruchomienie wybranej strony
    menu[choice](db)

if __name__ == "__main__":
    main()