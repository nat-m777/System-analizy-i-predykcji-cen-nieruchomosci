import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from src.auth import check_auth
from src.utils import get_db
from src.ml import PricePredictor
from src.i18n import LANGUAGES
T = LANGUAGES[st.session_state.get('lang', 'PL')]

# 1. Konfiguracja i zabezpieczenie
st.set_page_config(page_title="Wycena ML", layout="wide")
check_auth()

# --- INICJALIZACJA PAMIĘCI SESJI ---
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = None

def generate_pdf_report(username, area, rooms, city, district, price):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RAPORT INTELIGENTNEJ WYCENY", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Wygenerowano dla: {username} | Data: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Parametry wyceny:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"- Lokalizacja: {city}, {district}", ln=True)
    pdf.cell(0, 8, f"- Powierzchnia: {area} m2", ln=True)
    pdf.cell(0, 8, f"- Pokoje: {rooms}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 15, f"SUGEROWANA CENA: {price:,.2f} PLN".replace(",", " "), 1, ln=True, align='C', fill=True)
    return pdf.output(dest='S').encode('latin-1')

def main():
    st.title("Inteligentna Wycena Nieruchomości")
    
    db = get_db()
    predictor = PricePredictor()
    username = st.session_state.get('username')

    # --- ZARZĄDZANIE MODELEM ---
    with st.expander("⚙️ Zarządzanie modelem"):
        if st.button("🔄 Wytrenuj model"):
            df = db.get_all_offers(username)
            success, msg = predictor.train(df)
            if success: st.success(msg)
            else: st.warning(msg)

    # --- FORMULARZ ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        area = st.number_input("Metraż (m²)", min_value=10.0, value=40.0)
        rooms = st.slider("Liczba pokoi", 1, 10, 2)
    with col2:
        df_all = db.get_all_offers(username)
        if not df_all.empty:
            cities = sorted(df_all['city'].unique())
            city = st.selectbox("Miasto", cities)
            districts = sorted(df_all[df_all['city'] == city]['district'].unique())
            district = st.selectbox("Dzielnica", districts)
        else:
            st.error("Brak danych!")
            st.stop()

    # --- PRZYCISK OBLICZANIA ---
    if st.button("💰 Oblicz przewidywaną cenę", type="primary", use_container_width=True):
        price = predictor.predict(area, rooms, city, district)
        if price:
            # ZAPISUJEMY WYNIK DO SESJI
            st.session_state.last_prediction = {
                "price": price,
                "area": area,
                "rooms": rooms,
                "city": city,
                "district": district,
                "timestamp": datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            
            # Statystyki i Achievementy
            db.update_stat(username, "valuation_requests_count")
            new_medals = db.check_and_update_achievements(username)
            for m in new_medals: st.toast(f"🏆 Nowe osiągnięcie: {m}!")
        else:
            st.error("Błąd predykcji.")

    # --- WYŚWIETLANIE WYNIKU (TRWAŁE) ---
    # Ten blok kodu wykona się ZAWSZE, jeśli w sesji jest zapisana ostatnia wycena
    if st.session_state.last_prediction:
        res = st.session_state.last_prediction
        
        st.divider()
        st.subheader("🎯 Ostatni wynik wyceny")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.metric(
                label=f"Sugerowana cena dla {res['city']} ({res['district']})", 
                value=f"{res['price']:,.2f} PLN".replace(",", " "),
                delta=f"Parametry: {res['area']}m2, {res['rooms']} pok."
            )
        with c2:
            st.caption(f"Wygenerowano: {res['timestamp']}")

        # SEKCJA EKSPORTU (teraz nie zniknie po kliknięciu!)
        st.write("### 💾 Eksportuj wynik")
        e_col1, e_col2 = st.columns(2)
        
        with e_col1:
            res_df = pd.DataFrame([res])
            csv = res_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Pobierz CSV", data=csv, file_name="wycena.csv", mime="text/csv", use_container_width=True)
        
        with e_col2:
            pdf_bytes = generate_pdf_report(username, res['area'], res['rooms'], res['city'], res['district'], res['price'])
            st.download_button("📄 Pobierz Raport PDF", data=pdf_bytes, file_name="raport.pdf", mime="application/pdf", use_container_width=True)

if __name__ == "__main__":
    main()