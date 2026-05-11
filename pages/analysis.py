import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

# 1. NAPRAWA ŚCIEŻEK (Zawsze na górze)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_db, clean_df
from src.analysis.charts import show_price_prediction_logic
from src.auth import check_auth
from src.i18n import LANGUAGES

# 2. ZABEZPIECZENIE I JĘZYK
check_auth()
lang = st.session_state.get('lang', 'PL')
T = LANGUAGES[lang]

# 3. KONFIGURACJA STRONY
st.set_page_config(page_title=T["page_title"], layout="wide")

# --- INICJALIZACJA STANU SESJI ---
if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

def generate_valuation_pdf(username, city, district, area, rooms, price_est):
    """Generuje elegancki certyfikat wyceny w PDF używając tłumaczeń."""
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(41, 128, 185) 
    pdf.cell(0, 20, T["pdf_title"], ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Date/Data: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, T["pdf_params"], ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"- {T['city_label']}: {city}", ln=True)
    pdf.cell(0, 10, f"- {T['dist_label']}: {district}", ln=True)
    pdf.cell(0, 10, f"- {T['area_label']}: {area}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(235, 245, 251)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, f"VALUE: {int(price_est):,} PLN".replace(',', ' '), border=1, ln=True, align='C', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

def main():
    # USUNIĘTO: st.title("📈 Analiza...") - zostawiamy tylko wersję z T
    st.title(T["title"])
    
    db = get_db()
    username = st.session_state.get('username')

    if not username:
        st.error("Błąd sesji / Session Error")
        st.stop()

    df_raw = db.get_all_offers(username) 
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    st.divider()
    st.subheader(T["calc_header"])

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            in_city = st.selectbox(T["city_label"], options=sorted(df["city"].unique()), key="city_select")
            in_area = st.number_input(T["area_label"], min_value=10, max_value=500, value=50)
        with col2:
            available_districts = sorted(df[df["city"] == in_city]["district"].unique())
            in_dist = st.selectbox(T["dist_label"], options=available_districts, key="dist_select")
            in_rooms = st.slider(T["rooms_label"], 1, 10, 2)

        if st.button(T["calc_btn"], use_container_width=True):
            subset = df[(df['city'] == in_city) & (df['district'] == in_dist)]
            if subset.empty: subset = df[df['city'] == in_city]
            price_est = subset['price_per_m2'].mean() * in_area

            st.session_state.last_valuation = {
                "city": in_city, "district": in_dist, "area": in_area, "rooms": in_rooms, "price": price_est
            }

            db.update_stat(username, "valuation_requests_count")
            db.update_stat(username, "charts_generated_count")
            st.rerun()

    # --- WYNIKI ---
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        # Używamy .format() dla dynamicznych komunikatów
        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=f"{int(val['price']):,}"))
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv = pd.DataFrame([val]).to_csv(index=False).encode('utf-8-sig')
            st.download_button(T["download_csv"], data=csv, file_name="valuation.csv", use_container_width=True)
        
        with col_exp2:
            pdf_bytes = generate_valuation_pdf(username, val['city'], val['district'], val['area'], val['rooms'], val['price'])
            st.download_button(T["download_pdf"], data=pdf_bytes, file_name="valuation.pdf", use_container_width=True)

    # --- STATYSTYKI ---
    st.divider()
    with st.expander(T["stats_header"]):
        stats_df = df[df["city"] == in_city]
        if in_dist: stats_df = stats_df[stats_df["district"] == in_dist]
        
        if not stats_df.empty:
            col_m1, col_m2 = st.columns(2)
            col_m1.metric(T["avg_m2"], f"{round(stats_df['price_per_m2'].mean(), 2)} zł")
            col_m2.metric(T["median_m2"], f"{round(stats_df['price_per_m2'].median(), 2)} zł")
        else:
            st.write(T["no_data"])

if __name__ == "__main__":
    main()