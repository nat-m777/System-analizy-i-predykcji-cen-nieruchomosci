import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
from src.utils import get_db, clean_df
from src.analysis.charts import show_price_prediction_logic
from src.auth import check_auth

# --- KONFIGURACJA JĘZYKOWA ---
LANGUAGES = {
    "PL": {
        "page_title": "Analiza i Wycena",
        "title": "📈 Analiza Statystyczna i Wycena",
        "calc_header": "💡 Kalkulator szacunkowej ceny mieszkania",
        "city_label": "Wybierz miasto",
        "area_label": "Metraż (m²)",
        "dist_label": "Wybierz dzielnicę",
        "rooms_label": "Liczba pokoi",
        "calc_btn": "🚀 Oblicz estymację ceny",
        "result_msg": "Szacowana cena dla {city} ({dist}): {price} zł",
        "download_csv": "📥 Pobierz wynik (CSV)",
        "download_pdf": "📄 Pobierz Certyfikat (PDF)",
        "stats_header": "📊 Szybki podgląd statystyk lokalizacji",
        "chart_expander": "📊 Wykresy analizy rynkowej",
        "no_data": "⚠️ Brak danych do analizy.",
        "avg_m2": "Średnia m²",
        "median_m2": "Mediana m²",
        "pdf_title": "CERTYFIKAT WYCENY NIERUCHOMOSCI",
        "pdf_params": "Parametry analizy:",
        "comp_title": "🏙️ Analiza Porównawcza Miast",
        "comp_desc": "Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki.",
        "comp_config": "Konfiguracja Porównania",
        "comp_select_label": "Wybierz miasta (max 3):",
        "comp_info": "Wybierz miasta w panelu bocznym po lewej.",
        "comp_error_limit": "Proszę wybrać maksymalnie 3 miasta, aby zachować czytelność.",
        "comp_chart_avg": "1. Średnia cena za m²",
        "comp_chart_dist": "2. Rozkład metrażu",
        "comp_chart_scatter": "3. Relacja ceny do metrażu",
        "comp_table_header": "📊 Zestawienie liczbowe",
        "title_overview": "📊 Przegląd Rynku",
        "metric_offers": "Liczba ofert",
        "metric_cities": "Wybrane miasta",
        "tab_charts": "📊 Wykresy",
        "tab_cities": "🏙️ Miasta TOP 6",
        "export_header": "💾 Eksport i Raporty",
        "export_csv_desc": "Eksportuj 100 najlepszych ofert z filtrów:",
        "export_pdf_desc": "Generuj raport PDF (TOP 15 ofert):",
        "preview_header": "📋 Podgląd tabeli danych",
        "filters_header": "🔍 Filtry wyszukiwania",
        "save_search": "💾 Zapisz filtry",
        "login_title": "System Analizy Nieruchomości",
        "login_user": "Użytkownik",
        "login_pass": "Hasło",
        "login_btn": "Zaloguj",
        "reg_user": "Nowy użytkownik",
        "reg_pass": "Nowe hasło",
        "reg_btn": "Zarejestruj się",
        "logout_btn": "Wyloguj",
        "welcome_msg": "Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę."
    },
    "EN": {
        "page_title": "Analysis and Valuation",
        "title": "📈 Statistical Analysis & Valuation",
        "calc_header": "💡 Property Valuation Calculator",
        "city_label": "Select City",
        "area_label": "Area (sqm)",
        "dist_label": "Select District",
        "rooms_label": "Number of rooms",
        "calc_btn": "🚀 Calculate Estimated Price",
        "result_msg": "Estimated price for {city} ({dist}): {price} PLN",
        "download_csv": "📥 Download Result (CSV)",
        "download_pdf": "📄 Download Certificate (PDF)",
        "stats_header": "📊 Quick Location Stats",
        "chart_expander": "📊 Market Analysis Charts",
        "no_data": "⚠️ No data available for analysis.",
        "avg_m2": "Avg per m²",
        "median_m2": "Median per m²",
        "pdf_title": "PROPERTY VALUATION CERTIFICATE",
        "pdf_params": "Analysis parameters:",
        "comp_title": "🏙️ City Comparative Analysis",
        "comp_desc": "Select up to **3 cities** to compare their statistics.",
        "comp_config": "Comparison Configuration",
        "comp_select_label": "Select cities (max 3):",
        "comp_info": "Select cities in the sidebar on the left.",
        "comp_error_limit": "Please select a maximum of 3 cities for better readability.",
        "comp_chart_avg": "1. Average Price per m²",
        "comp_chart_dist": "2. Area Distribution",
        "comp_chart_scatter": "3. Price vs Area Relationship",
        "comp_table_header": "📊 Numerical Summary",
        "title_overview": "📊 Market Overview",
        "metric_offers": "Offer Count",
        "metric_cities": "Selected Cities",
        "tab_charts": "📊 Charts",
        "tab_cities": "🏙️ TOP 6 Cities",
        "export_header": "💾 Export & Reports",
        "export_csv_desc": "Export 100 best offers from filters:",
        "export_pdf_desc": "Generate PDF Report (TOP 15 offers):",
        "preview_header": "📋 Data Table Preview",
        "filters_header": "🔍 Search Filters",
        "save_search": "💾 Save Filters",
        "login_title": "Real Estate Analysis System",
        "login_user": "Username",
        "login_pass": "Password",
        "login_btn": "Login",
        "reg_user": "New Username",
        "reg_pass": "New Password",
        "reg_btn": "Create Account",
        "logout_btn": "Logout",
        "welcome_msg": "Select a module from the menu on the left to start working."
    }
}

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="Valuation App", layout="wide")

# 2. ZABEZPIECZENIE I INICJALIZACJA SESJI
check_auth()

if 'lang' not in st.session_state:
    st.session_state.lang = "PL"  # Domyślnie Polski

if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

# --- UI DO WYBORU JĘZYKA W SIDEBARZE ---
with st.sidebar:
    st.session_state.lang = st.radio("Language / Język", options=["PL", "EN"], index=0 if st.session_state.lang == "PL" else 1)

# Skrót do aktualnego języka
T = LANGUAGES[st.session_state.lang]

def generate_valuation_pdf(username, city, district, area, rooms, price_est):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(41, 128, 185) 
    pdf.cell(0, 20, T["pdf_title"], ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
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
            db.check_and_update_achievements(username)
            st.rerun()

    # --- WYŚWIETLANIE TRWAŁEGO WYNIKU ---
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=f"{int(val['price']):,}"))
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv = pd.DataFrame([val]).to_csv(index=False).encode('utf-8-sig')
            st.download_button(T["download_csv"], data=csv, file_name="valuation.csv", use_container_width=True)
        with col_exp2:
            pdf_bytes = generate_valuation_pdf(username, val['city'], val['district'], val['area'], val['rooms'], val['price'])
            st.download_button(T["download_pdf"], data=pdf_bytes, file_name="valuation.pdf", use_container_width=True)

    # --- STATYSTYKI NA DOLE ---
    st.divider()
    with st.expander(T["stats_header"]):
        stats_df = df[df["city"] == in_city]
        if in_dist: stats_df = stats_df[stats_df["district"] == in_dist]
        if not stats_df.empty:
            c1, c2 = st.columns(2)
            c1.metric(T["avg_m2"], f"{round(stats_df['price_per_m2'].mean(), 2)} zł")
            c2.metric(T["median_m2"], f"{round(stats_df['price_per_m2'].median(), 2)} zł")

if __name__ == "__main__":
    main()