import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

# 1. NAPRAWA ŚCIEŻEK (Kluczowe dla importu z src)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_db, clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
from src.auth import save_search, check_auth
from src.i18n import LANGUAGES

# 2. ZABEZPIECZENIE I JĘZYK
check_auth()
lang = st.session_state.get('lang', 'PL')
T = LANGUAGES[lang]

# 3. KONFIGURACJA STRONY
st.set_page_config(page_title=T.get("nav_home", "Dashboard"), layout="wide")

def generate_pdf_report(df, username, selected_cities):
    """Generuje raport PDF z tłumaczeniami."""
    pdf = FPDF()
    pdf.add_page()
    
    # Nagłówek
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"{T.get('pdf_title', 'Report')} - User: {username}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    # Podsumowanie
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, T.get("pdf_params", "Parameters:"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"- {T.get('city_label', 'Cities')}: {', '.join(selected_cities)}", ln=True)
    pdf.cell(0, 8, f"- {T.get('avg_m2', 'Avg/m2')}: {round(df['price_per_m2'].mean(), 0)} PLN/m2", ln=True)
    pdf.ln(5)

    # Logika wyboru 15 ofert
    num_cities = len(selected_cities)
    if num_cities > 0:
        per_city = max(1, 15 // num_cities)
        best_list = [df[df['city'] == c].sort_values('price_per_m2').head(per_city) for c in selected_cities]
        df_best = pd.concat(best_list).head(15)
    else:
        df_best = df.sort_values('price_per_m2').head(15)

    # Tabela PDF
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(35, 8, T.get("city_label", "City"), 1, 0, 'C', True)
    pdf.cell(60, 8, T.get("dist_label", "District"), 1, 0, 'C', True)
    pdf.cell(25, 8, T.get("area_label", "Area"), 1, 0, 'C', True)
    pdf.cell(30, 8, "Price", 1, 0, 'C', True)
    pdf.cell(30, 8, "PLN/m2", 1, 1, 'C', True)
    
    pdf.set_font("Arial", size=8)
    for _, row in df_best.iterrows():
        pdf.cell(35, 8, str(row['city']), 1)
        pdf.cell(60, 8, str(row.get('Dzielnica', 'N/A'))[:30], 1)
        pdf.cell(25, 8, f"{row['area']:.1f} m2", 1, 0, 'R')
        pdf.cell(30, 8, f"{int(row['price']):,} zl".replace(',', ' '), 1, 0, 'R')
        pdf.cell(30, 8, f"{int(row['price_per_m2']):,} zl".replace(',', ' '), 1, 1, 'R')
        
    return pdf.output(dest='S').encode('latin-1')

def render_sidebar(df, db, username):
    st.sidebar.success(f"{'Logged as' if lang == 'EN' else 'Zalogowany'}: **{username}**")
    if st.sidebar.button("Logout" if lang == "EN" else "Wyloguj"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.sidebar.header(T.get("filters_header", "🔍 Filtry"))
    all_cities = sorted(df["city"].unique())
    selected_cities = st.sidebar.multiselect(T.get("city_label", "City"), all_cities, default=all_cities)
    
    df_temp = df[df["city"].isin(selected_cities)]
    all_districts = sorted(df_temp["Dzielnica"].unique())
    selected_districts = st.sidebar.multiselect(T.get("dist_label", "District"), all_districts, default=all_districts)

    if st.sidebar.button(T.get("save_search", "💾 Zapisz wyszukiwanie")):
        save_search(username, selected_cities, selected_districts)
        st.sidebar.toast("Saved!" if lang == "EN" else "Zapisano!")

    # Trofea
    st.sidebar.divider()
    unlocked = db.get_user_achievements(username)
    badges = {"Badacz rynku": "🔍", "Eksplorator danych": "📈", "Porównywacz miast": "⚖️", "Specjalista od metrażu": "📏", "Ekspert wyceny": "💰"}
    cols = st.sidebar.columns(5)
    for i, (name, icon) in enumerate(badges.items()):
        is_u = name in unlocked
        cols[i].markdown(f"<div title='{name}' style='font-size:22px; filter:grayscale({0 if is_u else 100}%); opacity:{1 if is_u else 0.2};'>{icon}</div>", unsafe_allow_html=True)

    return selected_cities, selected_districts

def main():
    db = get_db()
    username = st.session_state.get('username')

    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    if df.empty:
        st.info(T["no_data"])
        return

    if "district" in df.columns: df = df.rename(columns={"district": "Dzielnica"})
    df["Dzielnica"] = df["Dzielnica"].astype(str)

    selected_cities, selected_districts = render_sidebar(df, db, username)

    # Filtrowanie
    df_filtered = df[df["city"].isin(selected_cities) & df["Dzielnica"].isin(selected_districts)].copy()

    st.title(T.get("title_overview", "📊 Przegląd Rynku"))
    
    m1, m2, m3 = st.columns(3)
    m1.metric(T.get("metric_offers", "Liczba ofert"), len(df_filtered))
    m2.metric(T.get("avg_m2", "Śr. cena/m²"), f"{round(df_filtered['price_per_m2'].mean(), 0)} zł" if not df_filtered.empty else "0 zł")
    m3.metric(T.get("metric_cities", "Wybrane miasta"), len(selected_cities))

    t1, t2 = st.tabs([T.get("tab_charts", "📊 Wykresy"), T.get("tab_cities", "🏙️ Miasta TOP 6")])
    with t1:
        st.plotly_chart(create_price_histogram(df_filtered), use_container_width=True)
        st.plotly_chart(create_area_vs_price_chart(df_filtered), use_container_width=True)
    with t2:
        top6 = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Łódź"]
        city_sel = st.selectbox(T.get("city_label", "Miasto"), [c for c in top6 if c in df["city"].unique()])
        if city_sel:
            db.update_stat(username, "charts_generated_count")
            city_data = df[df["city"] == city_sel].groupby("Dzielnica")["price_per_m2"].mean().sort_values().reset_index()
            st.plotly_chart(px.bar(city_data, x="Dzielnica", y="price_per_m2", color="price_per_m2"), use_container_width=True)

    # --- EKSPORT ---
    st.divider()
    st.subheader(T.get("export_header", "💾 Eksport danych"))
    c_exp1, c_exp2 = st.columns(2)

    with c_exp1:
        st.write(T.get("export_csv_desc", "Eksportuj 100 najlepszych ofert:"))
        df_csv = df_filtered.sort_values('price_per_m2').head(100)
        csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        st.download_button(T.get("download_csv", "📥 Pobierz CSV"), data=csv_data, file_name="top100_offers.csv", mime="text/csv")

    with c_exp2:
        st.write(T.get("export_pdf_desc", "Generuj raport PDF (TOP 15):"))
        if st.button(T.get("download_pdf", "📄 Generuj PDF")):
            pdf_bytes = generate_pdf_report(df_filtered, username, selected_cities)
            st.download_button("🔥 Download Report", data=pdf_bytes, file_name="market_report.pdf", mime="application/pdf")

    # Sprawdzanie osiągnięć
    new_m = db.check_and_update_achievements(username)
    for m in new_m: st.toast(f"🏆 {'New badge' if lang == 'EN' else 'Nowy medal'}: {m}!")

    st.divider()
    st.subheader(T.get("preview_header", "📋 Podgląd danych"))
    st.dataframe(df_filtered.head(50), use_container_width=True)

if __name__ == "__main__":
    main()