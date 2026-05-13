import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime
from fpdf import FPDF
from src.auth import check_auth
from src.utils import get_db, clean_df
from src.ml import PricePredictor
from src.lang import get_text

# 1. Konfiguracja i zabezpieczenie
st.set_page_config(page_title="ML Valuation", layout="wide")
check_auth()

# Pobranie tłumaczeń
T = get_text()

# --- INICJALIZACJA PAMIĘCI SESJI ---
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = None

def safe_text(text):
    """Usuwa polskie znaki dla standardowej czcionki FPDF (latin-1)."""
    if not text or pd.isna(text): return "N/A"
    return "".join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)).replace('ł', 'l').replace('Ł', 'L')

def generate_pdf_report(username, area, rooms, city, district, price):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Nagłówek
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, safe_text(T.get("pdf_title_ml", "RAPORT INTELIGENTNEJ WYCENY")), ln=True, align='C')
        
        pdf.set_font("Arial", size=10)
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
        pdf.cell(0, 10, safe_text(f"User: {username} | {T.get('pdf_date', 'Date')}: {date_str}"), ln=True, align='C')
        pdf.ln(10)
        
        # Parametry
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, safe_text(T.get("pdf_params", "Parametry wyceny:")), ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 8, safe_text(f"- {T.get('city_label', 'Miasto')}: {city}, {district}"), ln=True)
        pdf.cell(0, 8, safe_text(f"- {T.get('area_label', 'Metraz')}: {area} m2"), ln=True)
        pdf.cell(0, 8, safe_text(f"- {T.get('rooms_label', 'Pokoje')}: {rooms}"), ln=True)
        pdf.ln(10)
        
        # Wynik
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 14)
        price_text = f"{T.get('pdf_value', 'WARTOSC')}: {int(price):,}".replace(",", " ") + " PLN"
        pdf.cell(0, 15, safe_text(price_text), 1, ln=True, align='C', fill=True)
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

def main():
    st.title(T.get("ml_page_title", "Inteligentna Wycena Nieruchomości"))
    
    db = get_db()
    predictor = PricePredictor()
    username = st.session_state.get('username')

    # --- ZARZĄDZANIE MODELEM ---
    with st.expander(f"⚙️ {T.get('ml_manage_model', 'Zarzadzanie modelem')}"):
        if st.button(T.get("ml_train_btn", "🔄 Wytrenuj model")):
            df_raw = db.get_all_offers(username)
            df = clean_df(df_raw)
            success, msg = predictor.train(df)
            if success: st.success(msg)
            else: st.warning(msg)

    # --- FORMULARZ ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        area = st.number_input(T.get("area_label", "Metraz"), min_value=10.0, value=40.0)
        rooms = st.slider(T.get("rooms_label", "Pokoje"), 1, 10, 2)
    with col2:
        df_raw = db.get_all_offers(username)
        df = clean_df(df_raw)
        if df is not None and not df.empty:
            cities = sorted(df['city'].unique())
            city = st.selectbox(T.get("city_label", "Miasto"), cities)
            districts = sorted(df[df['city'] == city]['district'].unique())
            district = st.selectbox(T.get("dist_label", "Dzielnica"), districts)
        else:
            st.error(T.get("no_data", "Brak danych!"))
            st.stop()

    # --- PRZYCISK OBLICZANIA ---
    if st.button(T.get("ml_calc_btn", "💰 Oblicz przewidywana cene"), type="primary", use_container_width=True):
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
            st.rerun() # Odświeżamy, aby wynik wskoczył do UI
        else:
            st.error(T.get("ml_no_model", "Blad predykcji. Czy model jest wytrenowany?"))

    # --- WYŚWIETLANIE WYNIKU ---
    if st.session_state.last_prediction:
        res = st.session_state.last_prediction
        
        st.divider()
        st.subheader(f"🎯 {T.get('ml_last_result', 'Ostatni wynik wyceny')}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.metric(
                label=f"{T.get('result_msg_short', 'Sugerowana cena')}: {res['city']} ({res['district']})", 
                value=f"{int(res['price']):,}".replace(",", " ") + " PLN"
            )
        with c2:
            st.caption(f"{T.get('pdf_date', 'Data')}: {res['timestamp']}")

        # SEKCJA EKSPORTU
        st.write(f"### 💾 {T.get('export_header', 'Eksport i Raporty')}")
        e_col1, e_col2 = st.columns(2)
        
        with e_col1:
            res_df = pd.DataFrame([res])
            csv = res_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(T.get("download_csv", "Pobierz CSV"), data=csv, file_name="wycena_ml.csv", use_container_width=True)
        
        with e_col2:
            pdf_bytes = generate_pdf_report(username, res['area'], res['rooms'], res['city'], res['district'], res['price'])
            if pdf_bytes:
                st.download_button(T.get("download_pdf", "Pobierz PDF"), data=pdf_bytes, file_name="raport_ml.pdf", use_container_width=True)

if __name__ == "__main__":
    main()