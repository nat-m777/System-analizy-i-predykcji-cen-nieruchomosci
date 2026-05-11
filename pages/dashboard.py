import streamlit as st
import sys, os, pandas as pd, plotly.express as px
import unicodedata
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURACJA ŚCIEŻEK I IMPORTÓW ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import get_db, clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
from src.auth import save_search, check_auth, get_search_history, init_auth_db
from src.i18n import LANGUAGES

# --- FUNKCJE POMOCNICZE DANYCH ---

def safe_text(text):
    """Usuwa polskie znaki dla zgodności z PDF (latin-1)."""
    if not text or pd.isna(text):
        return "N/A"
    return "".join(
        c for c in unicodedata.normalize('NFKD', str(text))
        if not unicodedata.combining(c)
    ).replace('ł', 'l').replace('Ł', 'L')

def get_balanced_top_n(df, n, cities):
    """Pobiera po równo najlepszych ofert z każdego wybranego miasta."""
    if not cities or df.empty:
        return df.sort_values('price_per_m2').head(n)
    
    per_city = n // len(cities)
    remainder = n % len(cities)
    results = []
    
    for i, city in enumerate(sorted(cities)):
        # Jeśli n nie dzieli się równo, pierwsze miasta dostają o 1 ofertę więcej
        limit = per_city + (1 if i < remainder else 0)
        if limit > 0:
            city_top = df[df['city'] == city].sort_values('price_per_m2').head(limit)
            results.append(city_top)
            
    return pd.concat(results) if results else pd.DataFrame()

# --- ZABEZPIECZENIE I JĘZYK ---
check_auth() 
lang = st.session_state.get('lang', 'PL')
T = LANGUAGES.get(lang, LANGUAGES['PL'])
st.set_page_config(page_title="Dashboard Nieruchomości", layout="wide")

def init_session_state():
    if 'stats' not in st.session_state:
        st.session_state.stats = {"cities_viewed": set(), "charts_generated": 0, "valuation_requests": 0}

def mark_outliers(group):
    if len(group) < 5: return group.assign(status="✅ W normie")
    q1, q3 = group['price_per_m2'].quantile([0.25, 0.75])
    iqr = q3 - q1
    group['status'] = "✅ W normie"
    group.loc[group['price_per_m2'] < (q1 - 1.5 * iqr), 'status'] = "🔥 Okazja"
    group.loc[group['price_per_m2'] > (q3 + 1.5 * iqr), 'status'] = "💎 Premium"
    return group

def generate_top15_pdf(df, username, sel_cities):
    """PDF: 15 ofert podzielonych sprawiedliwie między wybrane miasta."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, safe_text(f"TOP 15 Najlepszych Ofert - Uzytkownik: {username}"), ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(200, 220, 255); pdf.set_font("Arial", 'B', 9)
    cols = [("Miasto", 30), ("Dzielnica", 50), ("Metraz", 25), ("Cena", 40), ("PLN/m2", 35)]
    for name, w in cols: pdf.cell(w, 10, name, 1, 0, 'C', True)
    pdf.ln(10)
    
    pdf.set_font("Arial", size=9)
    df_top = get_balanced_top_n(df, 15, sel_cities)
    
    for _, r in df_top.iterrows():
        pdf.cell(30, 10, safe_text(r['city']), 1)
        pdf.cell(50, 10, safe_text(r.get('Dzielnica', 'N/A'))[:25], 1)
        pdf.cell(25, 10, f"{r['area']:.1f} m2", 1, 0, 'R')
        pdf.cell(40, 10, f"{int(r['price']):,} zl".replace(',', ' '), 1, 0, 'R')
        pdf.cell(35, 10, f"{int(r['price_per_m2']):,} zl".replace(',', ' '), 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

def render_sidebar(df, db, username):
    st.sidebar.success(f"👤 Zalogowany: **{username}**")
    if st.sidebar.button("Wyloguj"):
        st.session_state['logged_in'] = False; st.rerun()
    st.sidebar.header("🔍 Filtry")
    all_cities = sorted(df["city"].unique())
    sel_cities = st.sidebar.multiselect("Wybierz Miasto", all_cities, default=all_cities)
    df_t = df[df["city"].isin(sel_cities)]
    sel_districts = st.sidebar.multiselect("Wybierz Dzielnicę", sorted(df_t["Dzielnica"].unique()), default=sorted(df_t["Dzielnica"].unique()))
    if st.sidebar.button("💾 Zapisz filtry"):
        save_search(username, sel_cities, sel_districts); st.sidebar.toast("Zapisano!")
    return sel_cities, sel_districts

def main():
    init_auth_db(); init_session_state(); db = get_db(); username = st.session_state.get('username')
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.title("📊 Przegląd Rynku"); st.info("Brak danych."); return

    df = df.rename(columns={"district": "Dzielnica"}) if "district" in df.columns else df
    df["Dzielnica"] = df["Dzielnica"].astype(str)
    
    sel_cities, sel_districts = render_sidebar(df, db, username)
    df_f = df[df["city"].isin(sel_cities) & df["Dzielnica"].isin(sel_districts)].copy()
    
    if df_f.empty:
        st.warning("⚠️ Brak ofert dla wybranych filtrów."); return

    df_f = df_f.groupby('Dzielnica', group_keys=False).apply(mark_outliers)

    st.title("📊 Przegląd Rynku Nieruchomości")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liczba ofert", len(df_f))
    m2.metric("Śr. cena/m²", f"{round(df_f['price_per_m2'].mean(), 0)} zł")
    m3.metric("🔥 Okazje", len(df_f[df_f['status'] == "🔥 Okazja"]))
    m4.metric("💎 Premium", len(df_f[df_f['status'] == "💎 Premium"]))

    tabs = st.tabs(["📊 Wykresy", "🏙️ Miasta TOP 6", "🚩 Anomalie", "📜 Historia"])
    
    with tabs[0]:
        if len(df_f) > 1:
            st.plotly_chart(create_price_histogram(df_f), use_container_width=True)
            st.plotly_chart(create_area_vs_price_chart(df_f), use_container_width=True)

    with tabs[1]:
        top6_list = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Łódź"]
        available_top6 = [c for c in top6_list if c in df["city"].unique()]
        if available_top6:
            city_sel = st.selectbox("Analiza dzielnic", available_top6)
            city_data = df[df["city"] == city_sel].groupby("Dzielnica")["price_per_m2"].mean().sort_values().reset_index()
            st.plotly_chart(px.bar(city_data, x="Dzielnica", y="price_per_m2", color="price_per_m2"), use_container_width=True)

    with tabs[2]:
        anom = df_f[df_f['status'] != "✅ W normie"]
        st.dataframe(anom.sort_values("price_per_m2"), use_container_width=True) if not anom.empty else st.info("Brak anomalii.")

    with tabs[3]:
        hist = get_search_history(username)
        if hist: st.dataframe(pd.DataFrame(hist), use_container_width=True)

    # --- SEKCOJA EKSPORTU ---
    st.divider(); st.subheader("📥 Eksportuj wyniki (zrównoważone)")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Top 100 ofert**")
        df_csv = get_balanced_top_n(df_f, 100, sel_cities)
        csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Pobierz TOP 100 CSV", data=csv_data, file_name="top100_ofert.csv", mime="text/csv")
    with c2:
        st.write("**Podsumowanie TOP 15**")
        if st.button("📄 Generuj raport PDF"):
            try:
                pdf_bytes = generate_top15_pdf(df_f, username, sel_cities)
                st.download_button("🔥 Pobierz gotowy PDF", data=pdf_bytes, file_name="top15_ofert.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Błąd PDF: {e}")
    
    st.divider(); st.subheader("📋 Podgląd danych")
    st.dataframe(df_f.sort_values("scrape_date", ascending=False).head(50), use_container_width=True)

if __name__ == "__main__":
    main()