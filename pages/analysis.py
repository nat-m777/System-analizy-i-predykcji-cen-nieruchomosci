import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime
from fpdf import FPDF
from src.utils import get_db, clean_df
from src.auth import check_auth
from src.lang import get_text # Pobieramy centralną funkcję tłumaczeń

# 1. KONFIGURACJA I ZABEZPIECZENIE
check_auth()
T = get_text() # Pobranie aktualnego słownika (PL lub EN)

st.set_page_config(page_title=T["page_title"], layout="wide")

# --- INICJALIZACJA STANU SESJI ---
if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

# --- LOGIKA GENEROWANIA PDF (Lokalnie w pliku) ---
def safe_text(text):
    """Usuwa polskie znaki dla standardowej czcionki FPDF."""
    if not text or pd.isna(text): return "N/A"
    return "".join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)).replace('ł', 'l').replace('Ł', 'L')

def generate_valuation_pdf(username, city, district, area, rooms, price_est):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Nagłówek
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(41, 128, 185) 
        pdf.cell(0, 20, safe_text(T["pdf_title"]), ln=True, align='C')
        
        # Data i Metadane
        pdf.set_font("Arial", size=10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"{safe_text(T['pdf_date'])}: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
        pdf.ln(10)
        
        # Parametry
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, safe_text(T["pdf_params"]), ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"- {safe_text(T['city_label'])}: {safe_text(city)}", ln=True)
        pdf.cell(0, 10, f"- {safe_text(T['dist_label'])}: {safe_text(district)}", ln=True)
        pdf.cell(0, 10, f"- {safe_text(T['area_label'])}: {area} m2", ln=True)
        pdf.cell(0, 10, f"- {safe_text(T['rooms_label'])}: {rooms}", ln=True)
        pdf.ln(10)
        
        # Wartość końcowa
        pdf.set_fill_color(235, 245, 251)
        pdf.set_font("Arial", 'B', 16)
        val_str = f"{T['pdf_value']}: {int(price_est):,} PLN".replace(',', ' ')
        pdf.cell(0, 20, safe_text(val_str), border=1, ln=True, align='C', fill=True)
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"{T['error_pdf']}: {e}")
        return None

def main():
    # Import lokalny dla uniknięcia pętli importów (circular import)
    from src.analysis.charts import show_price_prediction_logic
    
    st.title(T["title"])
    
    db = get_db()
    username = st.session_state.get('username')
    df_raw = db.get_all_offers(username) 
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    st.divider()
    st.subheader(T["calc_header"])

    # --- FORMULARZ WYCENY ---
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
            subset = df[(df['city'] == in_city) & (df['district'] == in_dist)].copy()
            if subset.empty: 
                subset = df[df['city'] == in_city].copy()
            
            avg_m2 = subset['price_per_m2'].mean()
            price_est = (avg_m2 if pd.notna(avg_m2) else 0) * in_area

            st.session_state.last_valuation = {
                "city": in_city, "district": in_dist, "area": in_area, "rooms": in_rooms, "price": price_est
            }
            db.update_stat(username, "valuation_requests_count")
            st.rerun()

    # --- SEKCYJNY WYNIK I EKSPORT ---
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=f"{int(val['price']):,}"))
        
        st.write(f"### 💾 {T.get('export_header', 'Eksport')}")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv = pd.DataFrame([val]).to_csv(index=False).encode('utf-8-sig')
            st.download_button(T["download_csv"], data=csv, file_name="valuation.csv", use_container_width=True)
        with col_exp2:
            pdf_bytes = generate_valuation_pdf(username, val['city'], val['district'], val['area'], val['rooms'], val['price'])
            if pdf_bytes:
                st.download_button(T["download_pdf"], data=pdf_bytes, file_name="valuation.pdf", use_container_width=True)

    # --- STATYSTYKI DODATKOWE ---
    st.divider()
    with st.expander(T["stats_header"]):
        stats_df = df[df["city"] == in_city]
        if in_dist: stats_df = stats_df[stats_df["district"] == in_dist]
        if not stats_df.empty:
            c1, c2 = st.columns(2)
            c1.metric(T["avg_m2"], f"{round(stats_df['price_per_m2'].mean(), 0)} zł")
            c2.metric(T["median_m2"], f"{round(stats_df['price_per_m2'].median(), 0)} zł")

if __name__ == "__main__":
    main()