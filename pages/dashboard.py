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
from src.lang import get_text

# --- ZABEZPIECZENIE I JĘZYK ---
check_auth() 
T = get_text()

def safe_text(text):
    """Usuwa polskie znaki dla biblioteki FPDF (standard latin-1)."""
    if not text or pd.isna(text): return "N/A"
    return "".join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)).replace('ł', 'l').replace('Ł', 'L')

def get_balanced_top_n(df, n, cities):
    if not cities or df.empty: return df.sort_values('price_per_m2').head(n)
    # ZABEZPIECZENIE: Usuwamy NaN przed sortowaniem i braniem TOP N
    df_clean = df.dropna(subset=['price', 'price_per_m2'])
    
    per_city = n // len(cities)
    remainder = n % len(cities)
    results = []
    for i, city in enumerate(sorted(cities)):
        limit = per_city + (1 if i < remainder else 0)
        if limit > 0:
            city_top = df_clean[df_clean['city'] == city].sort_values('price_per_m2').head(limit)
            results.append(city_top)
    return pd.concat(results) if results else pd.DataFrame()

def mark_outliers(group):
    status_norm = T.get("dash_status_norm", "✅ W normie")
    status_deal = T.get("dash_deals", "🔥 Okazja")
    status_premium = T.get("dash_premium", "💎 Premium")
    
    # Zabezpieczenie przed NaN w obliczeniach statystycznych
    if len(group) < 5 or group['price_per_m2'].isnull().all(): 
        return group.assign(status=status_norm)
        
    q1, q3 = group['price_per_m2'].quantile([0.25, 0.75])
    iqr = q3 - q1
    group['status'] = status_norm
    group.loc[group['price_per_m2'] < (q1 - 1.5 * iqr), 'status'] = status_deal
    group.loc[group['price_per_m2'] > (q3 + 1.5 * iqr), 'status'] = status_premium
    return group

def generate_top15_pdf(df, username, sel_cities):
    """Generuje raport PDF z najlepszymi ofertami korzystając z tłumaczeń."""
    pdf = FPDF()
    pdf.add_page()
    
    # Nagłówek raportu
    pdf.set_font("Arial", 'B', 16)
    title = f"{T.get('pdf_title', 'RAPORT')} - {username}"
    pdf.cell(0, 10, safe_text(title), ln=True, align='C')
    
    # Data
    pdf.set_font("Arial", size=10)
    date_str = f"{T.get('pdf_date', 'Date')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    pdf.cell(0, 10, date_str, ln=True, align='C')
    pdf.ln(10)
    
    # Nagłówki tabeli
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 9)
    cols = [
        (T.get("city_label", "City"), 35),
        (T.get("dist_label", "District"), 45),
        (T.get("area_label", "Area"), 25),
        (T.get("chart_price_label", "Price"), 40),
        ("PLN/m2", 35)
    ]
    
    for name, w in cols:
        pdf.cell(w, 10, safe_text(name), 1, 0, 'C', True)
    pdf.ln(10)
    
    # Dane tabeli
    pdf.set_font("Arial", size=9)
    # ZABEZPIECZENIE: Pobieramy dane i upewniamy się, że nie ma NaN
    df_top = get_balanced_top_n(df, 15, sel_cities)
    
    for _, r in df_top.iterrows():
        # Pobieranie wartości z zabezpieczeniem przed NaN dla funkcji int()
        raw_price = r['price'] if pd.notnull(r['price']) else 0
        raw_p_m2 = r['price_per_m2'] if pd.notnull(r['price_per_m2']) else 0
        raw_area = r['area'] if pd.notnull(r['area']) else 0

        pdf.cell(35, 10, safe_text(r['city']), 1)
        pdf.cell(45, 10, safe_text(r.get('Dzielnica', 'N/A'))[:22], 1)
        pdf.cell(25, 10, f"{raw_area:.1f} m2", 1, 0, 'R')
        pdf.cell(40, 10, f"{int(raw_price):,}".replace(',', ' '), 1, 0, 'R')
        pdf.cell(35, 10, f"{int(raw_p_m2):,}".replace(',', ' '), 1, 1, 'R')
        
    return pdf.output(dest='S').encode('latin-1')

def render_sidebar(df, db, username):
    st.sidebar.success(f"👤 {username}")
    if st.sidebar.button(T.get("logout_btn", "Logout")):
        from src.auth import logout_session
        logout_session()
        st.rerun()
        
    st.sidebar.header(T.get("dash_filters", "Filters"))
    all_cities = sorted(df["city"].unique())
    sel_cities = st.sidebar.multiselect(T.get("dash_select_city", "City"), all_cities, default=all_cities)
    
    df_t = df[df["city"].isin(sel_cities)]
    dist_col = "Dzielnica"
    all_dists = sorted(df_t[dist_col].unique())
    sel_districts = st.sidebar.multiselect(T.get("dash_select_dist", "District"), all_dists, default=all_dists)
    
    if st.sidebar.button(T.get("save_search", "Save")):
        save_search(username, sel_cities, sel_districts)
        st.sidebar.toast("Saved!")
    return sel_cities, sel_districts

def main():
    init_auth_db()
    db = get_db()
    username = st.session_state.get('username')
    
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.title(T.get("title_overview", "Market Overview"))
        st.info(T.get("no_data", "No data available"))
        return

    df = df.rename(columns={"district": "Dzielnica"}) if "district" in df.columns else df
    
    sel_cities, sel_districts = render_sidebar(df, db, username)
    df_f = df[df["city"].isin(sel_cities) & df["Dzielnica"].isin(sel_districts)].copy()
    
    if df_f.empty:
        st.warning(T.get("no_data", "No data"))
        return

    # Zabezpieczenie mark_outliers przed błędami NaN
    df_f = df_f.groupby('Dzielnica', group_keys=False).apply(mark_outliers)

    st.title(T.get("dash_title", "Market Overview"))
    
    # Metryki z zabezpieczeniem .fillna(0)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T.get("metric_offers", "Offers"), len(df_f))
    
    avg_val = df_f['price_per_m2'].mean()
    m2.metric(T.get("dash_avg_m2", "Avg price"), f"{round(avg_val if pd.notnull(avg_val) else 0, 0)} zł")
    
    deals_count = len(df_f[df_f['status'].str.contains("Okazja|Deal", na=False)])
    m3.metric(T.get("dash_deals", "Deals"), deals_count)
    
    premium_count = len(df_f[df_f['status'].str.contains("Premium", na=False)])
    m4.metric(T.get("dash_premium", "Premium"), premium_count)

    tabs = st.tabs([
        T.get("tab_charts", "Wykresy"), 
        T.get("tab_cities", "Miasta"), 
        T.get("dash_tab_anomalies", "Anomalie"), 
        T.get("dash_tab_history", "Historia")
    ])
    
    with tabs[0]:
        # Wykresy same w sobie zazwyczaj radzą sobie z NaN, ale lepiej podać przefiltrowane
        df_charts = df_f.dropna(subset=['price', 'area'])
        if len(df_charts) > 1:
            st.plotly_chart(create_price_histogram(df_charts), use_container_width=True)
            scatter_fig = create_area_vs_price_chart(df_charts)
            if scatter_fig:
                st.plotly_chart(scatter_fig, use_container_width=True)

    # ... (kod dla tabs[1], [2], [3] pozostaje bez zmian) ...
    # Sekcja eksportu (wykorzystuje poprawione funkcje wyżej)
    st.divider()
    st.subheader(T.get("dash_export_bal", "Export Results"))
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"**{T.get('export_csv_desc', 'TOP 100 Offers (CSV)')}**")
        df_csv = get_balanced_top_n(df_f, 100, sel_cities)
        csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label=T.get("dash_top100_csv", "Download CSV"), # Dodano domyślny tekst
            data=csv_data, 
            file_name="top100_offers.csv"
        )
    with c2:
        st.write(f"**{T.get('export_pdf_desc', 'TOP 15 Report (PDF)')}**")
        try:
            # Ta funkcja teraz rzutuje NaN na 0 przed int()
            pdf_data = generate_top15_pdf(df_f, username, sel_cities)
            st.download_button(
                label=T.get("dash_download_pdf"),
                data=pdf_data,
                file_name="market_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"{T.get('error_pdf', 'Error')}: {e}")

    st.divider()
    st.subheader(T.get("dash_preview"))
    st.dataframe(df_f.sort_values("scrape_date", ascending=False).head(50), use_container_width=True)

if __name__ == "__main__":
    main()