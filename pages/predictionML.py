import streamlit as st
import pandas as pd
from datetime import datetime
from src.auth import check_auth
from src.utils.database import get_db
from src.utils.data import clean_df
from src.ml import PricePredictor
from src.lang import get_text
from src.utils.export import generate_valuation_pdf, prepare_csv

# 1. Konfiguracja i zabezpieczenie
st.set_page_config(page_title="ML Valuation", layout="wide")
check_auth()

# Pobranie tłumaczeń JSON
T = get_text()

# --- INICJALIZACJA PAMIĘCI SESJI ---
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = None

def main():
    st.title(T.get("ml_page_title", "Inteligentna Wycena (Machine Learning)"))
    
    db = get_db()
    predictor = PricePredictor()
    username = st.session_state.get('username')

    # --- ZARZĄDZANIE MODELEM ---
    with st.expander(f"⚙️ {T.get('ml_manage_model', 'Zarządzanie modelem')}"):
        if st.button(T.get("ml_train_btn", "🔄 Wytrenuj model na danych"), use_container_width=True):
            df_raw = db.get_all_offers(username)
            df = clean_df(df_raw)
            success, msg = predictor.train(df)
            if success: 
                st.success(msg)
            else: 
                st.warning(msg)

    # --- FORMULARZ ---
    st.divider()
    col1, col2 = st.columns(2)
    
    # Pobieramy dane raz, aby wypełnić listy miast/dzielnic
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.error(T.get("no_data", "Brak danych do analizy!"))
        st.stop()

    with col1:
        area = st.number_input(T.get("area_label", "Metraż (m²)"), min_value=10.0, value=40.0)
        rooms = st.slider(T.get("rooms_label", "Liczba pokoi"), 1, 10, 2)
    
    with col2:
        cities = sorted(df['city'].unique())
        city = st.selectbox(T.get("city_label", "Miasto"), cities)
        districts = sorted(df[df['city'] == city]['district'].unique())
        district = st.selectbox(T.get("dist_label", "Dzielnica"), districts)

    # --- PRZYCISK OBLICZANIA ---
    if st.button(T.get("ml_calc_btn", "💰 Oblicz cenę przez AI"), type="primary", use_container_width=True):
        price = predictor.predict(area, rooms, city, district)
        if price:
            st.session_state.last_prediction = {
                "price": price,
                "area": area,
                "rooms": rooms,
                "city": city,
                "district": district,
                "timestamp": datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            db.update_stat(username, "valuation_requests_count")
            st.rerun()
        else:
            st.error(T.get("ml_no_model", "Błąd predykcji. Czy model jest wytrenowany?"))

    # --- WYŚWIETLANIE WYNIKU I EKSPORT ---
    if st.session_state.last_prediction:
        res = st.session_state.last_prediction
        
        st.divider()
        st.subheader(f"🎯 {T.get('ml_last_result', 'Ostatni wynik analizy')}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            formatted_price = f"{int(res['price']):,}".replace(",", " ")
            st.metric(
                label=f"{T.get('result_msg_short', 'Sugerowana wartość')}: {res['city']} ({res['district']})", 
                value=f"{formatted_price} PLN"
            )
        with c2:
            st.caption(f"{T.get('pdf_date', 'Data')}: {res['timestamp']}")

        # SEKCJA EKSPORTU (Używamy wspólnego modułu export.py)
        st.write(f"### 💾 {T.get('export_header', 'Eksport i Raporty')}")
        e_col1, e_col2 = st.columns(2)
        
        with e_col1:
            # Eksport CSV
            csv_bytes = prepare_csv(res)
            st.download_button(
                label=T.get("download_csv", "📥 Pobierz wynik (CSV)"),
                data=csv_bytes,
                file_name=f"ml_wycena_{res['city']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with e_col2:
            # Eksport PDF
            pdf_params = {
                T.get("city_label", "Miasto"): f"{res['city']}, {res['district']}",
                T.get("area_label", "Metraż"): f"{res['area']} m2",
                T.get("rooms_label", "Pokoje"): res['rooms'],
                "Metoda": "Machine Learning (Random Forest)"
            }
            
            pdf_bytes = generate_valuation_pdf(
                params=pdf_params, 
                price_est=res['price'], 
                translation_map=T
            )
            
            if pdf_bytes:
                st.download_button(
                    label=T.get("download_pdf", "📄 Pobierz Certyfikat (PDF)"),
                    data=pdf_bytes,
                    file_name=f"ml_raport_{res['city']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()