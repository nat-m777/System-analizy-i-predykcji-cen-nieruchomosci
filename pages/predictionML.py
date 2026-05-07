import streamlit as st
from src.auth import check_auth
from src.utils import get_db
from src.ml import PricePredictor

# 1. Zabezpieczenie strony
check_auth()

st.title("Inteligentna Wycena Nieruchomości")
st.markdown("Model Machine Learning przeanalizuje Twoje dane i porówna je z ofertami w bazie.")

db = get_db()
predictor = PricePredictor()

# --- SEKCJA TRENOWANIA ---
with st.expander("⚙️ Zarządzanie modelem"):
    if st.button("🔄 Wytrenuj model na moich danych"):
        df = db.get_all_offers(st.session_state['username'])
        success, msg = predictor.train(df)
        if success:
            st.success(msg)
        else:
            st.warning(msg)

# --- FORMULARZ PREDYKCJI ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    area = st.number_input("Metraż (m²)", min_value=10.0, max_value=500.0, value=40.0)
    rooms = st.slider("Liczba pokoi", 1, 10, 2)

with col2:
    # Pobieramy unikalne lokalizacje z Twojej bazy
    df_all = db.get_all_offers(st.session_state['username'])
    if not df_all.empty:
        cities = df_all['city'].unique()
        city = st.selectbox("Miasto", cities)
        districts = df_all[df_all['city'] == city]['district'].unique()
        district = st.selectbox("Dzielnica", districts)
    else:
        st.error("Brak danych w bazie. Najpierw coś pobierz!")
        st.stop()

if st.button("💰 Oblicz przewidywaną cenę", type="primary", use_container_width=True):
    price = predictor.predict(area, rooms, city, district)
    
    if price:
        st.metric("Sugerowana cena nieruchomości", f"{price:,.2f} PLN".replace(",", " "))
        st.info("💡 Cena bazuje na aktualnie pobranych ofertach w Twojej bazie.")
    else:
        st.error("Nie udało się dokonać predykcji. Upewnij się, że model jest wytrenowany.")