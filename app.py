import streamlit as st
import pandas as pd
import importlib
import time
from src.database.db_manager import DBManager
from src.scraper.otodom import OtodomScraper
from src.analysis.charts import(
    create_price_histogram, 
    create_area_vs_price_chart, 
    show_price_prediction_logic

)
# konfiguracja strony
st.set_page_config(
    page_title="Analiza Nieruchomości Pro",
    layout="wide",
    page_icon="🏠"
)

# style css
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.sidebar.warning("Plik assets/style.css nie został znaleziony.")

local_css("assets/style.css")

#inicjalizacja bazy
import src.database.db_manager as db_module
importlib.reload(db_module)

def get_db():
    db = DBManager()
    db.create_tables()
    return db

db = get_db()

# czyszczenie danych
def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Konwersje numeryczne
    numeric_cols = ["price", "area", "price_per_m2", "rooms"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Konwersje tekstowe
    text_cols = ["title", "city", "district", "source"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # Drop pustych rekordów krytycznych
    df = df.dropna(subset=["price", "area"])
    return df

#menu boczne
st.sidebar.header("Panel Sterowania")
menu_options = ["📊 Dashboard", "🕵️ Pobieranie Danych (Top 6)", "📈 Analiza Statystyczna", "🤖 Predykcja Ceny (ML)"]
page = st.sidebar.radio("Nawigacja:", menu_options)

# logika stron

# strona: daszboard
if page == "📊 Dashboard":
    st.title("📊 Przegląd Rynku Nieruchomości")
    
    df_raw = db.get_all_offers()
    df = clean_df(df_raw)

    
    if df.empty:
        st.info("Baza danych jest pusta. Przejdź do sekcji 'Pobieranie Danych', aby zasilić system.")
    else:
        # filtrowanie
        st.sidebar.subheader("Filtry")
        selected_cities = st.sidebar.multiselect(
            "Wybierz miasta:", 
            options=sorted(df['city'].unique()), 
            default=df['city'].unique()
        )
        
        df_filtered = df[df['city'].isin(selected_cities)]
        
        if df_filtered.empty:
            st.warning("Wybierz przynajmniej jedno miasto, aby wyświetlić dane.")
        else:
            # Metryki
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Liczba ofert", len(df_filtered))
            c2.metric("Śr. cena", f"{round(df_filtered['price'].mean()/1000, 1)} tys. zł")
            c3.metric("Śr. m²", f"{round(df_filtered['area'].mean(), 1)} m²")
            c4.metric("Śr. zł/m²", f"{round(df_filtered['price_per_m2'].mean(), 0)} zł")

            # Wykresy
            t1, t2 = st.tabs(["📉 Rozkład Cen", "🔍 Cena vs Powierzchnia"])
            with t1:
                st.plotly_chart(create_price_histogram(df_filtered), use_container_width=True)
            with t2:
                st.plotly_chart(create_area_vs_price_chart(df_filtered), use_container_width=True)

            st.subheader("📋 Ostatnie ogłoszenia")
            st.dataframe(df_filtered.sort_values('scrape_date', ascending=False), use_container_width=True)

#strona: scraper
elif page == "🕵️ Pobieranie Danych (Top 6)":
    st.title("🕵️ Selektywny Scraper Miast")
    
    available_cities = ["Warszawa", "Krakow", "Wroclaw", "Lodz", "Poznan", "Gdansk"]
    
    selected_to_scan = st.multiselect(
        "Wybierz miasta do pobrania danych:",
        options=available_cities,
        default=["Warszawa"]
    )
    
    if st.button("🚀 Uruchom Pobieranie dla Wybranych"):
        if not selected_to_scan:
            st.warning("Proszę wybrać przynajmniej jedno miasto.")
        else:
            scraper = OtodomScraper()
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, city in enumerate(selected_to_scan):
                status.info(f"Pobieranie danych dla: **{city}**... (Miasto {i+1}/{len(selected_to_scan)})")
                
                try:
                    df_city = scraper.fetch_data(city, max_pages=2)  
                    df_city = clean_df(df_city)
                    
                    if not df_city.empty:
                        db.insert_offers(df_city)
                        st.success(f"✅ {city}: Pobrano i zapisano {len(df_city)} ofert.")
                    else:
                        st.error(f"❌ {city}: Nie znaleziono ofert lub blokada serwera (403).")
                
                except Exception as e:
                    st.error(f"🔥 Błąd krytyczny dla {city}: {e}")
                
                progress_bar.progress((i + 1) / len(selected_to_scan))
                if i < len(selected_to_scan) - 1:
                    time.sleep(2)
            
            st.success("Proces zakończony.")
            st.balloons()

#strona: analiza statystyczna
elif page == "📈 Analiza Statystyczna":
    st.title("📈 Analiza Statystyczna")
    df_raw = db.get_all_offers()
    df = clean_df(df_raw)

    if df.empty:
        st.warning("⚠️ Baza danych jest pusta. Pobierz dane, aby dokonać wyceny.")
    else:
        with st.form("prediction_form"):
            c1, c2 = st.columns(2)
            with c1:
                area = st.number_input("Powierzchnia (m²)", 10, 500, 50)
                city = st.selectbox("Miasto", sorted(df['city'].unique()))
            with c2:
                rooms = st.slider("Pokoje", 1, 6, 2)
                districts = sorted(df[df['city'] == city]['district'].unique())
                district = st.selectbox("Dzielnica", districts)
            
            submit = st.form_submit_button("Oblicz wartość")

        if submit:
            show_price_prediction_logic(df, area, city, district)

#strona: predykcja machine learning
elif page == "🤖 Predykcja Ceny (ML)":
    st.title("🤖 Estymator Wartości Mieszkania")
    with st.form("ml_form"):
        area = st.number_input("Powierzchnia (m²)", 20, 150, 50)
        rooms = st.slider("Liczba pokoi", 1, 5, 2)
        city = st.selectbox("Miasto", ["Warszawa", "Krakow", "Wroclaw", "Lodz", "Poznan", "Gdansk"])
        if st.form_submit_button("Wyceń mieszkanie"):
            st.success("Wkrótce połączymy to z modelem RandomForest!")