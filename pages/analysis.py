import streamlit as st
import pandas as pd
from src.utils import get_db, clean_df
from src.analysis.charts import show_price_prediction_logic
from src.auth import check_auth

# 1. KONFIGURACJA (Zawsze na samym początku)
st.set_page_config(page_title="Analiza i Wycena", layout="wide")

# 2. ZABEZPIECZENIE
check_auth()

def main():
    st.title("📈 Analiza Statystyczna i Wycena")
    
    # 1. POBIERANIE DANYCH
    db = get_db()
    
    # Sprawdzamy czy mamy username w sesji przed pobraniem
    if 'username' not in st.session_state:
        st.error("Błąd sesji: Nie znaleziono nazwy użytkownika.")
        st.stop()

    # PRAWIDŁOWE POBIERANIE (Tylko raz, z argumentem)
    username = st.session_state['username']
    df_raw = db.get_all_offers(username) 
    
    # Czyszczenie danych
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {username} nie posiada danych do analizy. Uruchom scraper!")
        return

    # --- SEKCJA: KALKULATOR WYCENY ---
    st.divider()
    st.subheader("💡 Kalkulator szacunkowej ceny mieszkania")
    st.info("Kalkulator oblicza cenę na podstawie średnich rynkowych z pobranych ofert.")

    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            in_city = st.selectbox(
                "Wybierz miasto", 
                options=sorted(df["city"].unique()),
                key="city_select"
            )
            in_area = st.number_input("Metraż (m²)", min_value=10, max_value=500, value=50)

        with col2:
            available_districts = sorted(df[df["city"] == in_city]["district"].unique())
            in_dist = st.selectbox(
                "Wybierz dzielnicę", 
                options=available_districts,
                key="dist_select"
            )
            in_rooms = st.slider("Liczba pokoi", 1, 10, 2)

        if st.button("🚀 Oblicz estymację ceny", use_container_width=True):
            show_price_prediction_logic(df, in_area, in_city, in_dist)

    # --- SEKCJA: DODATKOWE STATYSTYKI ---
    st.divider()
    with st.expander("📊 Zobacz statystyki dla wybranej lokalizacji"):
        stats_df = df[df["city"] == in_city]
        if in_dist:
            stats_df = stats_df[stats_df["district"] == in_dist]
        
        if not stats_df.empty:
            # Upewnij się, że kolumna price_per_m2 istnieje po clean_df
            avg_price = stats_df["price_per_m2"].mean()
            median_price = stats_df["price_per_m2"].median()
            min_price = stats_df["price_per_m2"].min()
            max_price = stats_df["price_per_m2"].max()
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                st.metric("Średnia m²", f"{round(avg_price, 2)} zł")
            with col_m2:
                st.metric("Mediana m²", f"{round(median_price, 2)} zł")
            with col_m3:
                st.metric("Min m²", f"{round(min_price, 2)} zł")
            with col_m4:
                st.metric("Max m²", f"{round(max_price, 2)} zł")
                
            st.caption(f"Statystyki oparte na {len(stats_df)} ofertach.")
        else:
            st.write("Zbyt mało danych dla tej lokalizacji.")

if __name__ == "__main__":
    main()