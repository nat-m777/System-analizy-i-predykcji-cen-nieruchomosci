import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

# 1. NAPRAWA ŚCIEŻEK (Zawsze na górze)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.database import get_db
from src.utils.data import clean_df
from src.auth import check_auth

from src.lang import get_text
T = get_text()

# 2. ZABEZPIECZENIE I JĘZYK
check_auth()

# 3. KONFIGURACJA STRONY (Zawsze przed jakimkolwiek rysowaniem UI)
st.set_page_config(page_title=T.get("nav_comparision", "Porównanie Miast"), layout="wide")

def main():
    # Używamy kluczy ze słownika T (upewnij się, że masz je w i18n.py)
    st.title(T.get("comp_title", "🏙️ Analiza Porównawcza Miast"))
    st.markdown(T.get("comp_desc", "Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki."))

    if 'username' not in st.session_state:
        st.error("Błąd sesji / Session Error")
        st.stop()
    
    username = st.session_state['username']
    db = get_db()
    
    # 3. POBIERANIE DANYCH
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    # --- PANEL BOCZNY ---
    st.sidebar.header(T.get("comp_config", "Konfiguracja Porównania"))
    real_cities_in_db = sorted(df["city"].unique())

    selected_cities = st.sidebar.multiselect(
        T.get("comp_select_label", "Wybierz miasta (max 3):"),
        options=real_cities_in_db,
        default=real_cities_in_db[:3] if len(real_cities_in_db) >= 3 else real_cities_in_db
    )   
    
    if not selected_cities:
        st.info(T.get("comp_info", "Wybierz miasta w panelu bocznym."))
        return

    # --- BLOKADA > 3 ---
    if len(selected_cities) > 3:
        st.error(T.get("comp_error_limit", "Proszę wybrać maksymalnie 3 miasta."))
        return

    # --- LOGIKA OSIĄGNIĘĆ (bez zmian, działa w tle) ---
    if "cities_compared_total" not in st.session_state:
        st.session_state.cities_compared_total = set()

    st.session_state.cities_compared_total.update(selected_cities)
    total_compared = len(st.session_state.cities_compared_total)
    db.update_stat(username, "cities_viewed_count", value=total_compared, increment=False)

    # --- FILTROWANIE I WYKRESY ---
    df_comp = df[df["city"].isin(selected_cities)].copy()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(T.get("comp_chart_avg", "1. Średnia cena za m²"))
        avg_price = df_comp.groupby("city")["price_per_m2"].mean().sort_values().reset_index()
        fig1 = px.bar(avg_price, x="city", y="price_per_m2", color="city", text_auto='.0f')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader(T.get("comp_chart_dist", "2. Rozkład metrażu"))
        fig2 = px.box(df_comp, x="city", y="area", color="city", points=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader(T.get("comp_chart_scatter", "3. Relacja ceny do metrażu"))
    fig3 = px.scatter(df_comp, x="area", y="price", color="city", hover_data=["city", "district"])
    st.plotly_chart(fig3, use_container_width=True)

    # TABELA
    st.subheader(T.get("comp_table_header", "📊 Zestawienie liczbowe"))
    summary = df_comp.groupby("city").agg({"price_per_m2": ["mean", "median"], "price": "count"}).reset_index()
    
    # Nazwy kolumn tabeli też powinny być tłumaczone
    summary.columns = [
        T.get("col_city", "Miasto"), 
        T.get("avg_m2", "Średnia PLN/m²"), 
        T.get("median_m2", "Mediana PLN/m²"), 
        T.get("col_count", "Liczba ofert")
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()