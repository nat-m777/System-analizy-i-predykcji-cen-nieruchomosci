import plotly.express as px
import streamlit as st

def create_price_histogram(df):
    """Tworzy histogram rozkładu cen mieszkań."""
    fig = px.histogram(
        df, 
        x="price", 
        nbins=30, 
        title="Rozkład cen nieruchomości",
        labels={'price': 'Cena (PLN)', 'count': 'Liczba ofert'},
        color_discrete_sequence=['#007bff']
    )
    fig.update_layout(bargap=0.1)
    return fig

def create_area_vs_price_chart(df):
    """Tworzy wykres punktowy: Powierzchnia vs Cena."""
    fig = px.scatter(
        df, 
        x="area", 
        y="price", 
        color="rooms",
        size="price_per_m2",
        hover_name="title",
        title="Zależność ceny od powierzchni (kolor = liczba pokoi)",
        labels={'area': 'Powierzchnia (m²)', 'price': 'Cena (PLN)', 'rooms': 'Pokoje'}
    )
    return fig

def show_price_prediction_logic(df, area, city, district):
    """Oblicza estymację i zwraca komponenty wizualne."""
    # 1. Filtrowanie danych
    local_data = df[(df['city'] == city) & (df['district'] == district)]
    scope = f"dzielnicy {district}"

    if len(local_data) < 3:
        local_data = df[df['city'] == city]
        scope = f"miasta {city}"

    if local_data.empty:
        st.error(f"Brak danych dla lokalizacji: {city}")
        return

    # 2. Obliczenia
    median_price_m2 = local_data['price_per_m2'].median()
    estimated_value = area * median_price_m2

    # 3. Wyświetlanie metryk
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Przewidywana wartość rynkowa", 
            value=f"{int(estimated_value):,} PLN".replace(",", " ")
        )
    with col2:
        st.metric(
            label="Mediana cen w tej okolicy", 
            value=f"{int(median_price_m2):,} PLN/m²".replace(",", " ")
        )
    
    st.info(f"💡 Wycena oparta na analizie ofert z obszaru: **{scope}**.")

    # 4. Wykres kontekstowy
    fig_comp = px.box(
        local_data, 
        y="price_per_m2", 
        title=f"Gdzie plasuje się Twoja wycena? (Rozkład cen w {scope})",
        points="all",
        color_discrete_sequence=['#28a745']
    )
    st.plotly_chart(fig_comp, use_container_width=True)