import streamlit as st
import pandas as pd
import numpy as np
from src.auth import check_auth
from src.utils import get_db, clean_df
from src.ml import PricePredictor, get_statistical_estimate

# 1. Konfiguracja i Auth
st.set_page_config(page_title="Pojedynek Wycen", layout="wide")
check_auth()

st.title("⚖️ Statystyka vs Machine Learning")
st.markdown("Sprawdź, jak różnią się wyniki tradycyjnej analizy średnich od modelu predykcyjnego.")

# 2. Pobranie danych
db = get_db()
username = st.session_state['username']
df_raw = db.get_all_offers(username)
df = clean_df(df_raw)

if df is None or df.empty:
    st.warning("Pobierz dane scraperem, aby skorzystać z porównania.")
    st.stop()

# 3. Formularz wejściowy
with st.sidebar:
    st.header("Parametry nieruchomości")
    city = st.selectbox("Miasto", sorted(df['city'].unique()))
    districts = sorted(df[df['city'] == city]['district'].unique())
    district = st.selectbox("Dzielnica", districts)
    area = st.number_input("Metraż (m²)", 10.0, 500.0, 50.0)
    rooms = st.slider("Liczba pokoi", 1, 10, 2)

# 4. Obliczenia
predictor = PricePredictor()
ml_price = predictor.predict(area, rooms, city, district)
stat_price = get_statistical_estimate(df, area, city, district)

# 5. Prezentacja Wyników
col1, col2, col3 = st.columns(3)

if stat_price and ml_price:
    diff = ml_price - stat_price
    diff_percent = (diff / stat_price) * 100

    with col1:
        st.metric("Wycena Statystyczna", f"{stat_price:,.0f} zł".replace(",", " "))
        st.caption("Oparta na średniej cenie m² w lokalizacji")

    with col2:
        st.metric("Wycena Machine Learning", f"{ml_price:,.0f} zł".replace(",", " "), 
                  delta=f"{diff:,.0f} zł", delta_color="normal")
        st.caption("Oparta na modelu Random Forest")

    with col3:
        sentiment = "📈 Wyższa niż średnia" if diff > 0 else "📉 Niższa niż średnia"
        st.metric("Różnica metod", f"{abs(diff_percent):.1f}%", delta=sentiment)

    # 6. Wykres Porównawczy
    st.divider()
    
    # Tworzymy dane do wykresu
    comparison_df = pd.DataFrame({
        "Metoda": ["Statystyka (Średnia)", "Machine Learning"],
        "Cena [PLN]": [stat_price, ml_price]
    })
    
    import plotly.express as px
    fig = px.bar(comparison_df, x="Metoda", y="Cena [PLN]", color="Metoda", 
                 text_auto='.2s', title="Porównanie kwotowe")
    st.plotly_chart(fig, use_container_width=True)

    # 7. Wyjaśnienie różnic
    with st.expander("🧐 Dlaczego wyniki się różnią?"):
        st.write("""
        * **Wycena statystyczna** mnoży Twój metraż przez średnią cenę m² w dzielnicy. Nie wie jednak, czy 50m² to 2 czy 3 pokoje.
        * **Machine Learning** widzi zależność między metrażem a liczbą pokoi. Zauważa np., że mniejsze mieszkania mają zazwyczaj wyższą cenę za metr niż wielkie apartamenty (efekt skali).
        * Jeśli cena ML jest niższa, może to oznaczać, że Twoja konfiguracja (np. dużo pokoi na małym metrażu) jest rzadsza lub mniej ceniona przez rynek niż sugerowałaby prosta średnia.
        """)
else:
    st.info("Wytrenuj model ML w zakładce Predykcja, aby zobaczyć porównanie.")