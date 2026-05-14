import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

# --- 1. KONFIGURACJA ŚCIEŻEK ---
# Naprawa ścieżek dostępu, aby Python mógł importować moduły z folderu głównego (np. src/)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.database import get_db
from src.utils.data import clean_df
from src.auth import check_auth
from src.lang import get_text

# Inicjalizacja słownika tłumaczeń (i18n)
T = get_text()

# --- 2. ZABEZPIECZENIE I KONFIGURACJA ---
# Sprawdzenie autoryzacji (czy użytkownik jest zalogowany)
check_auth()

# Konfiguracja metadanych strony - musi być wywołana przed elementami UI
st.set_page_config(page_title=T.get("nav_comparision", "Porównanie Miast"), layout="wide")

def main():
    """
    Główna funkcja modułu porównywarki miast.
    Umożliwia zestawienie statystyk cenowych i metrażowych dla maksymalnie 3 lokalizacji.
    """
    st.title(T.get("comp_title", "🏙️ Analiza Porównawcza Miast"))
    st.markdown(T.get("comp_desc", "Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki."))

    # Weryfikacja obecności nazwy użytkownika w sesji
    if 'username' not in st.session_state:
        st.error("Błąd sesji / Session Error")
        st.stop()
    
    username = st.session_state['username']
    db = get_db()
    
    # --- 3. POBIERANIE I PRZYGOTOWANIE DANYCH ---
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    # Obsługa przypadku, gdy baza ofert jest pusta
    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    # --- PANEL BOCZNY (SIDEBAR) ---
    st.sidebar.header(T.get("comp_config", "Konfiguracja Porównania"))
    real_cities_in_db = sorted(df["city"].unique())

    # Wybór miast do porównania (z ograniczeniem domyślnym do 3 pierwszych)
    selected_cities = st.sidebar.multiselect(
        T.get("comp_select_label", "Wybierz miasta (max 3):"),
        options=real_cities_in_db,
        default=real_cities_in_db[:3] if len(real_cities_in_db) >= 3 else real_cities_in_db
    )   
    
    # Walidacja wyboru
    if not selected_cities:
        st.info(T.get("comp_info", "Wybierz miasta w panelu bocznym."))
        return

    if len(selected_cities) > 3:
        st.error(T.get("comp_error_limit", "Proszę wybrać maksymalnie 3 miasta."))
        return

    # --- LOGIKA SYSTEMU OSIĄGNIĘĆ ---
    # Śledzenie unikalnych miast, które użytkownik kiedykolwiek porównywał
    if "cities_compared_total" not in st.session_state:
        st.session_state.cities_compared_total = set()

    st.session_state.cities_compared_total.update(selected_cities)
    total_compared = len(st.session_state.cities_compared_total)
    
    # Aktualizacja statystyki "cities_viewed_count" w bazie danych (bez inkrementacji, nadpisujemy wartość)
    db.update_stat(username, "cities_viewed_count", value=total_compared, increment=False)

    # --- FILTROWANIE DANYCH ---
    # Tworzymy podzbiór danych zawierający tylko wybrane miasta
    df_comp = df[df["city"].isin(selected_cities)].copy()
    
    # --- SEKCJA WIZUALIZACJI ---
    col1, col2 = st.columns(2)
    
    with col1:
        # Wykres słupkowy średnich cen za metr kwadratowy
        st.subheader(T.get("comp_chart_avg", "1. Średnia cena za m²"))
        avg_price = df_comp.groupby("city")["price_per_m2"].mean().sort_values().reset_index()
        fig1 = px.bar(avg_price, x="city", y="price_per_m2", color="city", text_auto='.0f')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Wykres pudełkowy (box plot) pokazujący rozpiętość metraży mieszkań w miastach
        st.subheader(T.get("comp_chart_dist", "2. Rozkład metrażu"))
        fig2 = px.box(df_comp, x="city", y="area", color="city", points=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    
    # Wykres punktowy (scatter) relacji ceny całkowitej do powierzchni
    st.subheader(T.get("comp_chart_scatter", "3. Relacja ceny do metrażu"))
    fig3 = px.scatter(df_comp, x="area", y="price", color="city", hover_data=["city", "district"])
    st.plotly_chart(fig3, use_container_width=True)

    # --- TABELA PODSUMOWUJĄCA ---
    st.subheader(T.get("comp_table_header", "📊 Zestawienie liczbowe"))
    
    # Agregacja danych: średnia, mediana oraz liczność ofert dla każdego miasta
    summary = df_comp.groupby("city").agg({
        "price_per_m2": ["mean", "median"], 
        "price": "count"
    }).reset_index()
    
    # Mapowanie technicznych nazw kolumn na przetłumaczone nagłówki UI
    summary.columns = [
        T.get("col_city", "Miasto"), 
        T.get("avg_m2", "Średnia PLN/m²"), 
        T.get("median_m2", "Mediana PLN/m²"), 
        T.get("col_count", "Liczba ofert")
    ]
    
    # Wyświetlenie tabeli z ukryciem indeksu
    st.dataframe(summary, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()