import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils.database import get_db
from src.utils.data import clean_df
from src.auth import check_auth
from src.lang import get_text

# =========================================================
# 1. KONFIGURACJA STRONY (Musi być na samej górze)
# =========================================================
# Pobieramy teksty przed configiem, ale bez renderowania UI
T = get_text()

st.set_page_config(
    page_title=f"{T.get('page_title', 'Analiza')} - Ranking", 
    layout="wide"
)

# =========================================================
# 2. LOGIKA DANYCH (Łatwa do testowania automatycznego)
# =========================================================

def get_ranking_data(df):
    """Filtruje dane tylko dla kluczowych miast i ujednolica nazwy."""
    city_map = {
        "warszawa": "Warszawa",
        "kraków": "Kraków", "krakow": "Kraków",
        "wrocław": "Wrocław", "wroclaw": "Wrocław",
        "gdańsk": "Gdańsk", "gdansk": "Gdańsk",
        "poznań": "Poznań", "poznan": "Poznań",
        "łódź": "Łódź", "lodz": "Łódź"
    }
    
    df = df.copy()
    df["city_lower"] = df["city"].str.lower().str.strip()
    df_ranking = df[df["city_lower"].isin(city_map.keys())].copy()
    df_ranking["city"] = df_ranking["city_lower"].map(city_map)
    return df_ranking

def apply_filters(df):
    """Renderuje filtry w sidebarze i zwraca przefiltrowany DataFrame."""
    st.sidebar.header(f"⚖️ {T.get('dash_filters', 'Filtry')}")

    # Powierzchnia
    min_a, max_a = int(df["area"].min()), int(df["area"].max())
    selected_area = st.sidebar.slider(
        f"{T.get('area_label', 'Metraż')}:", 
        min_value=10, max_value=250, 
        value=(min_a, max_a), step=5
    )

    # Pokoje
    real_rooms = sorted(df["rooms"].unique())
    selected_rooms = st.sidebar.multiselect(
        f"{T.get('rooms_label', 'Pokoje')}:", 
        options=real_rooms, default=real_rooms
    )

    mask = (
        (df["area"] >= selected_area[0]) & 
        (df["area"] <= selected_area[1]) &
        (df["rooms"].isin(selected_rooms))
    )
    return df[mask]

# =========================================================
# 3. KOMPONENTY UI (Wizualizacja)
# =========================================================

def render_ranking_chart(df):
    """Tworzy i wyświetla wykres słupkowy."""
    st.subheader(f"📊 {T.get('comp_chart_avg', 'Porównanie cen')}")
    
    if df.empty:
        st.info(T.get("no_data", "Brak danych dla wybranych filtrów."))
        return

    # Agregacja
    stats = df.groupby("city").agg({
        "price_per_m2": "mean",
        "price": "count" 
    }).reset_index().sort_values("price_per_m2", ascending=False)

    fig = px.bar(
        stats, x="city", y="price_per_m2", color="city",
        text_auto='.0f',
        labels={
            "price_per_m2": T.get('dash_avg_m2', "PLN/m²"), 
            "city": T.get('dash_select_city', "Miasto")
        },
        hover_data=["price"]
    )
    st.plotly_chart(fig, use_container_width=True)
    return stats

def render_ranking_table(stats):
    """Wyświetla sformatowaną tabelę z wynikami."""
    st.divider()
    st.subheader(f"📑 {T.get('comp_table_header', 'Tabela')}")
    
    display_df = stats.rename(columns={
        "city": T.get('dash_select_city', "Miasto"),
        "price_per_m2": T.get('dash_avg_m2', "Średnia PLN/m²"),
        "price": T.get('metric_offers', "Liczba Ofert")
    })
    
    st.dataframe(
        display_df.style.format({T.get('dash_avg_m2', "Średnia PLN/m²"): "{:.0f}"}),
        use_container_width=True, hide_index=True
    )

# =========================================================
# 4. GŁÓWNA FUNKCJA STERUJĄCA
# =========================================================

def main():
    check_auth()
    
    st.title(f"🏆 {T.get('tab_cities', 'Ranking Miast')}")
    st.markdown(T.get('comp_desc', "Porównaj ceny mieszkań dla **TOP 6** miast."))

    db = get_db()
    username = st.session_state.get('username')

    if not username:
        st.error(T.get('error_db', "Zaloguj się ponownie."))
        st.stop()

    # Przepływ danych
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T.get("no_data", "Brak danych."))
        return

    # Przetwarzanie
    df_ranking = get_ranking_data(df)
    
    if df_ranking.empty:
        st.warning(T.get("no_data", "Brak ofert w TOP 6."))
        return

    # Interfejs i Filtry
    df_filtered = apply_filters(df_ranking)
    
    # Prezentacja
    stats = render_ranking_chart(df_filtered)
    if stats is not None:
        render_ranking_table(stats)

if __name__ == "__main__":
    main()