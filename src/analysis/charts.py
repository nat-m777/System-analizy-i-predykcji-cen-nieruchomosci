import plotly.express as px
import streamlit as st
from src.lang import get_text

def create_price_histogram(df):
    T = get_text()
    """Tworzy histogram rozkładu cen mieszkań."""
    # Usuwamy NaN z kolumny price, aby uniknąć błędów renderowania
    df_clean = df.dropna(subset=['price'])
    
    fig = px.histogram(
        df_clean, 
        x="price", 
        nbins=30, 
        title=T.get("comp_chart_dist", "Rozkład cen nieruchomości"),
        labels={'price': 'Cena (PLN)', 'count': 'Liczba ofert'},
        color_discrete_sequence=['#007bff']
    )
    fig.update_layout(bargap=0.1)
    return fig

def create_area_vs_price_chart(df):
    T = get_text()
    """Tworzy wykres punktowy: Powierzchnia vs Cena."""
    
    # KLUCZOWA POPRAWKA: Usuwamy wiersze, które mają NaN w kolumnach używanych na wykresie
    # Jeśli rooms lub price_per_m2 są puste, Plotly wygeneruje błąd 'size' lub 'color'
    df_clean = df.dropna(subset=['area', 'price', 'rooms', 'price_per_m2'])
    
    if df_clean.empty:
        return None

    fig = px.scatter(
        df_clean, 
        x="area", 
        y="price", 
        color="rooms",
        size="price_per_m2",
        hover_name="title" if "title" in df_clean.columns else None,
        title=T.get("comp_chart_scatter", "Zależność ceny od powierzchni"),
        labels={'area': T.get("area_label", 'Powierzchnia'), 'price': 'Cena (PLN)', 'rooms': T.get("rooms_label", 'Pokoje')}
    )
    return fig

def show_price_prediction_logic(df, area, city, district):
    T = get_text()
    """Oblicza estymację i zwraca komponenty wizualne."""
    
    # 1. Filtrowanie danych i obsługa braków
    local_data = df[(df['city'] == city) & (df['district'] == district)].copy()
    local_data = local_data.dropna(subset=['price_per_m2']) # Ważne dla mediany
    
    scope = f"{T.get('dist_label', 'dzielnicy')} {district}"

    if len(local_data) < 3:
        local_data = df[df['city'] == city].copy().dropna(subset=['price_per_m2'])
        scope = f"{T.get('city_label', 'miasta')} {city}"

    if local_data.empty:
        st.error(T.get("no_data", "Brak danych"))
        return

    # 2. Obliczenia
    median_price_m2 = local_data['price_per_m2'].median()
    estimated_value = area * median_price_m2

    # 3. Wyświetlanie metryk
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label=T.get("calc_btn", "Przewidywana wartość"), 
            value=f"{int(estimated_value):,} PLN".replace(",", " ")
        )
    with col2:
        st.metric(
            label=T.get("median_m2", "Mediana"), 
            value=f"{int(median_price_m2):,} PLN/m²".replace(",", " ")
        )
    
    st.info(f"💡 {T.get('comp_info', 'Info')}: **{scope}**.")

    # 4. Wykres kontekstowy
    fig_comp = px.box(
        local_data, 
        y="price_per_m2", 
        title=f"{T.get('stats_header', 'Statystyki')} ({scope})",
        points="all",
        color_discrete_sequence=['#28a745']
    )
    st.plotly_chart(fig_comp, use_container_width=True)