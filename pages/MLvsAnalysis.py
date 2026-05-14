import streamlit as st
import pandas as pd
import plotly.express as px
from src.auth import check_auth
from src.utils.database import get_db
from src.utils.data import clean_df
from src.ml import PricePredictor, get_statistical_estimate
from src.lang import get_text 

# =========================================================
# 1. KONFIGURACJA STRONY
# =========================================================
T = get_text()

st.set_page_config(
    page_title=T.get("duel_page_title", "Pojedynek"), 
    layout="wide"
)

# =========================================================
# 2. LOGIKA DANYCH I PARAMETRÓW
# =========================================================

def get_sidebar_inputs(df):
    """Renderuje formularz w sidebarze i zwraca parametry wyceny."""
    with st.sidebar:
        st.header(T.get("duel_params_header", "Parametry nieruchomości"))
        
        city = st.selectbox(
            T.get("city_label", "Miasto"), 
            sorted(df['city'].unique())
        )
        
        districts = sorted(df[df['city'] == city]['district'].unique())
        district = st.selectbox(
            T.get("dist_label", "Dzielnica"), 
            districts
        )
        
        area = st.number_input(
            T.get("area_label", "Metraż (m²)"), 
            10.0, 500.0, 50.0
        )
        
        rooms = st.slider(
            T.get("rooms_label", "Liczba pokoi"), 
            1, 10, 2
        )
        
    return city, district, area, rooms

def calculate_valuations(df, area, rooms, city, district):
    """Przeprowadza wycenę obiema metodami."""
    predictor = PricePredictor()
    ml_price = predictor.predict(area, rooms, city, district)
    stat_price = get_statistical_estimate(df, area, city, district)
    return ml_price, stat_price

# =========================================================
# 3. KOMPONENTY UI
# =========================================================

def render_metrics(stat_price, ml_price):
    """Wyświetla porównanie wycen w kolumnach."""
    col1, col2, col3 = st.columns(3)
    
    diff = ml_price - stat_price
    diff_percent = (diff / stat_price) * 100

    with col1:
        st.metric(
            T.get("duel_stat_val", "Wycena Statystyczna"), 
            f"{stat_price:,.0f} PLN".replace(",", " ")
        )
        st.caption(T.get("duel_stat_cap", "Oparta na średniej cenie m²"))

    with col2:
        st.metric(
            T.get("duel_ml_val", "Wycena Machine Learning"), 
            f"{ml_price:,.0f} PLN".replace(",", " "), 
            delta=f"{diff:,.0f} PLN", 
            delta_color="normal"
        )
        st.caption(T.get("duel_ml_cap", "Oparta na modelu Random Forest"))

    with col3:
        sentiment = T.get("duel_higher", "📈 Wyższa") if diff > 0 else T.get("duel_lower", "📉 Niższa")
        st.metric(
            T.get("duel_diff_label", "Różnica metod"), 
            f"{abs(diff_percent):.1f}%", 
            delta=sentiment
        )

def render_comparison_chart(stat_price, ml_price):
    """Wyświetla wykres słupkowy porównujący obie metody."""
    st.divider()
    
    comparison_df = pd.DataFrame({
        T.get("duel_method_col", "Metoda"): [T.get("duel_stat_val", "Statystyka"), T.get("duel_ml_val", "ML")],
        T.get("duel_price_col", "Cena [PLN]"): [stat_price, ml_price]
    })
    
    fig = px.bar(
        comparison_df, 
        x=T.get("duel_method_col", "Metoda"), 
        y=T.get("duel_price_col", "Cena [PLN]"), 
        color=T.get("duel_method_col", "Metoda"), 
        text_auto='.2s', 
        title=T.get("duel_chart_title", "Porównanie kwotowe")
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 4. GŁÓWNA FUNKCJA STERUJĄCA
# =========================================================

def main():
    check_auth()
    
    st.title(T.get("duel_title", "⚖️ Statystyka vs Machine Learning"))
    st.markdown(T.get("duel_desc", "Sprawdź, jak różnią się wyniki tradycyjnej analizy średnich od modelu predykcyjnego."))

    # Inicjalizacja danych
    db = get_db()
    username = st.session_state.get('username')
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T.get("no_data", "Brak danych."))
        return

    # Formularz wejściowy
    city, district, area, rooms = get_sidebar_inputs(df)

    # Obliczenia
    ml_price, stat_price = calculate_valuations(df, area, rooms, city, district)

    # Prezentacja wyników
    if stat_price and ml_price:
        render_metrics(stat_price, ml_price)
        render_comparison_chart(stat_price, ml_price)

        # Wyjaśnienie różnic
        with st.expander(T.get("duel_expander_title", "🧐 Dlaczego wyniki się różnią?")):
            st.markdown(T.get("duel_explanation", "Brak tłumaczenia wyjaśnienia."))
    else:
        st.info(T.get("duel_no_model", "Wytrenuj model ML, aby zobaczyć porównanie."))

if __name__ == "__main__":
    main()