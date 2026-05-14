import streamlit as st
import pandas as pd
from src.utils.database import get_db
from src.utils.data import clean_df
from src.utils.export import generate_valuation_pdf
from src.auth import check_auth
from src.lang import get_text
from src.utils.export import generate_valuation_pdf, prepare_csv

# 1. KONFIGURACJA I ZABEZPIECZENIE
check_auth()
T = get_text()  # Pobranie słownika z plików JSON (src/i18n/)

st.set_page_config(page_title=T["page_title"], layout="wide")

# --- INICJALIZACJA STANU SESJI ---
if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

def main():
    # Import lokalny dla uniknięcia circular import
    from src.analysis.charts import show_price_prediction_logic
    
    st.title(T["title"])
    
    # Pobieranie i czyszczenie danych
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
            # Prosta logika wyceny statystycznej
            subset = df[(df['city'] == in_city) & (df['district'] == in_dist)].copy()
            if subset.empty: 
                subset = df[df['city'] == in_city].copy()
            
            avg_m2 = subset['price_per_m2'].mean()
            price_est = (avg_m2 if pd.notna(avg_m2) else 0) * in_area

            # Zapisanie wyniku do sesji
            st.session_state.last_valuation = {
                "city": in_city, 
                "district": in_dist, 
                "area": in_area, 
                "rooms": in_rooms, 
                "price": price_est,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            # Statystyki użycia w bazie
            db.update_stat(username, "valuation_requests_count")
            st.rerun()

    # --- SEKCJA WYNIKÓW I EKSPORTU ---
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        # Wykresy (logika z charts.py)
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        # Komunikat o sukcesie z wyceną
        formatted_price = f"{int(val['price']):,}".replace(',', ' ')
        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=formatted_price))
        
        # --- PANEL EKSPORTU ---
        st.write(f"### 💾 {T.get('export_header', 'Eksport danych')}")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Eksport do CSV (używając nowej funkcji z export.py)
            csv_bytes = prepare_csv(val)
            st.download_button(
                label=T["download_csv"],
                data=csv_bytes,
                file_name=f"wycena_{val['city']}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with col_exp2:
            # Przygotowanie parametrów do PDF i generowanie
            pdf_params = {
                T["city_label"]: val['city'],
                T["dist_label"]: val['district'],
                T["area_label"]: f"{val['area']} m²",
                T["rooms_label"]: val['rooms']
            }
            
            pdf_bytes = generate_valuation_pdf(pdf_params, val['price'], T)
            
            if pdf_bytes:
                st.download_button(
                    label=T["download_pdf"],
                    data=pdf_bytes,
                    file_name=f"certyfikat_{val['city']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # --- DODATKOWE STATYSTYKI LOKALIZACJI ---
    st.divider()
    with st.expander(T["stats_header"]):
        stats_df = df[df["city"] == in_city]
        if in_dist: 
            stats_df = stats_df[stats_df["district"] == in_dist]
            
        if not stats_df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric(T["avg_m2"], f"{round(stats_df['price_per_m2'].mean(), 0)} zł")
            c2.metric(T["median_m2"], f"{round(stats_df['price_per_m2'].median(), 0)} zł")
            c3.metric(T["metric_offers"], len(stats_df))
        else:
            st.info(T["no_data"])

if __name__ == "__main__":
    from datetime import datetime # Import potrzebny do timestampa
    main()