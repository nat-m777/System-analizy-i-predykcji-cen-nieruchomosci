import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df

from src.auth import check_auth

check_auth()

st.set_page_config(page_title="Porównanie TOP 6", layout="wide")

def main():
    st.title("🏙️ Analiza Porównawcza Miast TOP 6")
    st.markdown("Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki na czytelnych wykresach.")

    # 1. DANE
    db = get_db()
    df = clean_df(db.get_all_offers())
    
    if df.empty:
        st.warning("Brak danych w bazie.")
        return

    # Filtrujemy tylko miasta z TOP 6
    top6_list = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Łódź"]
    available_top6 = [c for c in top6_list if c in df["city"].unique()]

    # --- PANEL BOCZNY (WYBÓR) ---
    st.sidebar.header("Konfiguracja Porównania")

    # Zamiast wpisywać listę ręcznie, pobierzmy to, co faktycznie jest w bazie:
    real_cities_in_db = sorted(df["city"].unique())

    selected_cities = st.sidebar.multiselect(
        "Wybierz miasta do porównania (max 3):",
        options=real_cities_in_db,
        default=real_cities_in_db[:3] if len(real_cities_in_db) >= 3 else real_cities_in_db
    )   
    if len(selected_cities) > 3:
        st.error("Proszę wybrać maksymalnie 3 miasta, aby zachować czytelność.")
        return
    
    if not selected_cities:
        st.info("Wybierz miasta w panelu bocznym.")
        return

    # Filtrowanie danych do wybranych miast
    df_comp = df[df["city"].isin(selected_cities)].copy()

    # --- TRZY WYKRESY ANALITYCZNE ---
    
    col1, col2 = st.columns(2)

    with col1:
        # WYKRES 1: Średnia cena za m2 w miastach
        st.subheader("1. Średnia cena za m²")
        avg_price = df_comp.groupby("city")["price_per_m2"].mean().sort_values().reset_index()
        fig1 = px.bar(
            avg_price, x="city", y="price_per_m2", 
            color="city", text_auto='.0f',
            labels={"price_per_m2": "PLN/m²", "city": "Miasto"}
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # WYKRES 2: Rozkład metrażu ofert
        st.subheader("2. Typowy metraż (Boxplot)")
        fig2 = px.box(
            df_comp, x="city", y="area", color="city",
            labels={"area": "Powierzchnia (m²)", "city": "Miasto"},
            points=False # ukrywamy outlierów dla przejrzystości
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # WYKRES 3 (Pełna szerokość): Relacja Cena vs Metraż
    st.subheader("3. Relacja ceny do metrażu")
    fig3 = px.scatter(
        df_comp, x="area", y="price", color="city", 
        hover_data=["district"], opacity=0.6,
        labels={"area": "Metraż", "price": "Cena całkowita (PLN)"}
    )
    st.plotly_chart(fig3, use_container_width=True)

    # --- TABELA PODSUMOWUJĄCA ---
    st.subheader("📊 Zestawienie liczbowe")
    summary = df_comp.groupby("city").agg({
        "price_per_m2": ["mean", "median"],
        "price": "count"
    }).reset_index()
    summary.columns = ["Miasto", "Średnia PLN/m²", "Mediana PLN/m²", "Liczba ofert"]
    st.table(summary.style.format({
        "Średnia PLN/m²": "{:.0f}",
        "Mediana PLN/m²": "{:.0f}"
    }))

if __name__ == "__main__":
    main()