import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Importy z Twojej struktury src
from src.utils.database import get_db
from src.utils.data import clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
from src.auth import save_search, check_auth, get_search_history, init_auth_db
from src.lang import get_text
from src.utils.export import generate_valuation_pdf

# --- 1. ZABEZPIECZENIE I JĘZYK ---
check_auth() 
T = get_text() 
username = st.session_state.get('username', 'User')

def get_balanced_top_n(df, n, cities):
    """
    Pomocnicza funkcja do wyboru zrównoważonych ofert do raportu.
    """
    if not cities or df.empty: 
        return df.sort_values('price_per_m2').head(n)
    
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
    """
    Oznacza okazje i oferty premium na podstawie rozkładu IQR wewnątrz grupy dzielnicowej.
    """
    status_norm = T.get("dash_status_norm", "✅ W normie")
    status_deal = T.get("dash_deals", "🔥 Okazja")
    status_premium = T.get("dash_premium", "💎 Premium")
    
    if len(group) < 5 or group['price_per_m2'].isnull().all(): 
        return group.assign(status=status_norm)
        
    q1, q3 = group['price_per_m2'].quantile([0.25, 0.75])
    iqr = q3 - q1  # <-- Tutaj była usterka, teraz jest już w 100% poprawnie
    
    group['status'] = status_norm
    group.loc[group['price_per_m2'] < (q1 - 1.5 * iqr), 'status'] = status_deal
    group.loc[group['price_per_m2'] > (q3 + 1.5 * iqr), 'status'] = status_premium
    return group

def render_dashboard_ui(df, sel_cities, sel_districts, avg_val, history_df, all_cities, df_raw_for_dists):
    """
    Interfejs użytkownika renderujący wszystkie wykresy, metryki i odseparowaną historię rynkową.
    """
    st.title(f"Witaj {username}! 👋")
    st.info(T.get("welcome_msg", "Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę."))
    
    st.divider()
    st.subheader(T.get("dash_title", "Przegląd Rynku"))
    
    avg_total_price = df['price'].mean() if 'price' in df.columns else 0
    
    # --- OBLICZENIA STATYSTYK ---
    m2_series = df['price_per_m2'].dropna()
    if not m2_series.empty:
        med_val = m2_series.median()
        min_val = m2_series.min()
        max_val = m2_series.max()
    else:
        med_val = min_val = max_val = 0
    
    # --- METRYKI ---
    st.markdown("### 📊 Ogólne podsumowanie")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T.get("metric_offers", "Oferty"), f"{len(df)} szt.")
    m2.metric(T.get("dash_avg_total", "Śr. cena całkowita"), 
             f"{int(avg_total_price):,}".replace(",", " ") + " zł" if pd.notnull(avg_total_price) else "0 zł")
    
    deals_count = len(df[df['status'].str.contains("Okazja|Deal", na=False)]) if 'status' in df.columns else 0
    m3.metric(T.get("dash_deals", "Okazje rynkowe"), f"{deals_count} szt.")
    premium_count = len(df[df['status'].str.contains("Premium", na=False)]) if 'status' in df.columns else 0
    m4.metric(T.get("dash_premium", "Oferty Premium"), f"{premium_count} szt.")

    st.write("") 
    st.markdown("### 📐 Analiza szczegółowa ceny za m²")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("📉 Średnia cena za m²", f"{round(avg_val if pd.notnull(avg_val) else 0, 0):,} zł/m²".replace(",", " "))
    s2.metric("⚖️ Mediana za m²", f"{round(med_val, 0):,} zł/m²".replace(",", " "))
    s3.metric("🟢 Minimalna cena za m²", f"{round(min_val, 0):,} zł/m²".replace(",", " "))
    s4.metric("🔴 Maksymalna cena za m²", f"{round(max_val, 0):,} zł/m²".replace(",", " "))

    # --- ZAKŁADKI (TABS) ---
    tabs = st.tabs([
        T.get("tab_charts", "Wykresy"), 
        T.get("dash_tab_anomalies", "Analiza Okazji"), 
        T.get("dash_tab_history", "Historia wyszukiwań"),
        T.get("dash_preview", "Podgląd danych")
    ])
    
    with tabs[0]:
        df_charts = df.dropna(subset=['price', 'area'])
        if len(df_charts) > 1:
            st.plotly_chart(create_price_histogram(df_charts), use_container_width=True)
            fig_area_price = create_area_vs_price_chart(df_charts)
            if fig_area_price is not None:
                st.plotly_chart(fig_area_price, use_container_width=True)
        else:
            st.warning(T.get("no_data_charts", "Zbyt mało danych do generowania wykresów."))

    with tabs[1]:
        st.write(T.get("anomalies_desc", "Oferty odbiegające cenowo od średniej in danej dzielnicy:"))
        if 'status' in df.columns:
            st.dataframe(
                df[df['status'] != T.get("dash_status_norm", "✅ W normie")].sort_values("price_per_m2"),
                use_container_width=True
            )

    with tabs[2]:
        # =========================================================================
        # 📋 INTERAKTYWNA TABELA HISTORII (ODSEPAROWANA - TAG [DASH])
        # =========================================================================
        if history_df is not None and not history_df.empty:
            
            # Filtrujemy dane tak, aby wyświetlić wyłącznie rekordy z tagiem [DASH]
            if "Dzielnice" in history_df.columns:
                history_df = history_df[history_df["Dzielnice"].astype(str).str.contains(r"\[DASH\]", na=False)]
                
            recent_searches = history_df.head(10)
            
            if not recent_searches.empty:
                col_h1, col_h2, col_h3, col_h4 = st.columns([2, 3, 3, 2])
                with col_h1: st.markdown("**Data**")
                with col_h2: st.markdown("**Miasta**")
                with col_h3: st.markdown("**Dzielnice**")
                with col_h4: st.markdown("**Akcja**")
                st.markdown("---")
                
                for idx, row in recent_searches.iterrows():
                    saved_date = row.get("Data", "")
                    saved_cities_raw = row.get("Miasta", "")
                    saved_districts_raw = row.get("Dzielnice", "")
                    
                    # Oczyszczamy string wyświetlania z technicznego prefiksu
                    clean_districts_display = str(saved_districts_raw).replace("[DASH] ", "")
                    
                    c1, c2, c3, c4 = st.columns([2, 3, 3, 2])
                    with c1: st.write(str(saved_date))
                    with c2: st.write(str(saved_cities_raw))
                    with c3: st.caption(clean_districts_display)
                    with c4:
                        if st.button("Wczytaj 🔄", key=f"load_dash_{idx}", use_container_width=True):
                            parsed_cities = [c.strip() for c in str(saved_cities_raw).split(",") if c.strip() in all_cities]
                            
                            if parsed_cities:
                                st.session_state["dash_sel_cities"] = parsed_cities
                                pure_districts_string = clean_districts_display
                                
                                if pure_districts_string.strip().lower() in ["wszystkie", ""]:
                                    if "dash_sel_districts" in st.session_state:
                                        del st.session_state["dash_sel_districts"]
                                else:
                                    df_temp = df_raw_for_dists[df_raw_for_dists["city"].isin(parsed_cities)]
                                    available_dists = set(str(d).strip() for d in df_temp["district"].unique() if d)
                                    parsed_dists = [d.strip() for d in pure_districts_string.split(",") if d.strip() in available_dists]
                                    st.session_state["dash_sel_districts"] = parsed_dists
                                
                                st.toast("🔄 Załadowano filtry do panelu bocznego!")
                                st.rerun()
                            else:
                                st.error("Nie udało się dopasować miast z tego rekordu.")
            else:
                st.info("Brak zapisanych wyszukiwań dla głównego Dashboardu.")
        else:
            st.info(T.get("no_history", "Brak historii wyszukiwań."))

    with tabs[3]:
        st.dataframe(df.sort_values("price_per_m2", ascending=True), use_container_width=True)

    # --- EKSPORT ---
    st.divider()
    st.subheader(T.get("dash_export_bal", "Eksport Wyników"))
    c1, c2 = st.columns(2)
    with c1:
        df_csv = get_balanced_top_n(df, 100, sel_cities)
        csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label=T.get("dash_top100_csv", "Pobierz CSV"), data=csv_data, file_name="export.csv", mime="text/csv", use_container_width=True)
    with c2:
        pdf_params = {T.get("city_label", "Miasta"): ", ".join(sel_cities), T.get("metric_offers", "Liczba ofert"): len(df), T.get("dash_avg_total", "Śr. cena"): f"{int(avg_total_price):,} zł"}
        pdf_bytes = None
        try: pdf_bytes = generate_valuation_pdf(pdf_params, avg_val, T)
        except Exception: pass
        if pdf_bytes is not None:
            st.download_button(label=T.get("dash_download_pdf", "Pobierz Raport PDF"), data=pdf_bytes, file_name="market_report.pdf", mime="application/pdf", use_container_width=True)

def main():
    init_auth_db()
    db = get_db()
    
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw) 
    
    if df is None or df.empty:
        st.title(f"Witaj {username}! 👋")
        st.info(T.get("no_data", "Brak danych w bazie."))
        return

    if "city" in df.columns:
        df["city"] = df["city"].str.replace(r'[\r\n\t]+', '', regex=True).str.strip()
    if "district" in df.columns:
        df["district"] = df["district"].str.replace(r'[\r\n\t]+', '', regex=True).str.strip()

    # --- FILTRY Sidebaru ---
    st.sidebar.header(T.get("dash_filters", "Filtry"))
    all_cities = sorted([str(c).strip() for c in df["city"].unique() if c and str(c).lower() != 'none'])
    
    # Inicjalizacja stanu sesji dla miast dashboardu
    if "dash_sel_cities" not in st.session_state:
        st.session_state["dash_sel_cities"] = all_cities

    sel_cities = st.sidebar.multiselect(
        T.get("dash_select_city", "Miasto"), 
        all_cities, 
        default=st.session_state["dash_sel_cities"]
    )
    st.session_state["dash_sel_cities"] = sel_cities
    
    if "district" in df.columns:
        df_t = df[df["city"].isin(sel_cities)]
        all_dists = sorted([str(d).strip() for d in df_t["district"].unique() if d and str(d).lower() not in ['none', 'nan']])
        
        # Inicjalizacja stanu sesji dla dzielnic dashboardu
        if "dash_sel_districts" not in st.session_state:
            st.session_state["dash_sel_districts"] = all_dists
            
        current_allowed_dists = [d for d in st.session_state["dash_sel_districts"] if d in all_dists]
        if not current_allowed_dists and all_dists:
            current_allowed_dists = all_dists

        sel_districts = st.sidebar.multiselect(
            T.get("dash_select_dist", "Dzielnica"), 
            all_dists, 
            default=current_allowed_dists
        )
        st.session_state["dash_sel_districts"] = sel_districts
        df_f = df[df["city"].isin(sel_cities) & df["district"].isin(sel_districts)].copy()
    else:
        sel_districts = []
        df_f = df[df["city"].isin(sel_cities)].copy()

    # =========================================================================
    # 💾 ZAPIS HISTORII Z TAGIEM [DASH]
    # =========================================================================
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Zapisz to wyszukiwanie", use_container_width=True):
        if sel_cities:
            try:
                miasta_str = ", ".join(sel_cities)
                dzielnice_str = ", ".join(sel_districts) if sel_districts else "Wszystkie"
                
                # Zapisujemy tag [DASH] bezpośrednio w kolumnie szczegółów
                save_search(username, miasta_str, f"[DASH] {dzielnice_str}")
                st.toast("✅ Wyszukiwanie zapisane w historii!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Nie udało się zapisać: {e}")
        else:
            st.sidebar.warning("Wybierz przynajmniej jedno miasto, aby zapisać.")
        
    # --- POBIERANIE HISTORII ---
    try:
        history_raw = get_search_history(username)
        if history_raw:
            if isinstance(history_raw, list) and len(history_raw) > 0 and isinstance(history_raw[0], (tuple, list)):
                history_df = pd.DataFrame(history_raw, columns=["Użytkownik", "Miasta", "Dzielnice"])
            else:
                history_df = pd.DataFrame(history_raw)
        else:
            history_df = pd.DataFrame()
    except Exception:
        history_df = pd.DataFrame()

    if df_f.empty:
        st.warning(T.get("no_data_filters", "Brak danych dla wybranych filtrów."))
        return

    if "district" in df_f.columns:
        df_f = df_f.groupby("district", group_keys=False).apply(mark_outliers)
    else:
        df_f['status'] = T.get("dash_status_norm", "✅ W normie")

    avg_val = df_f['price_per_m2'].mean()
    render_dashboard_ui(df_f, sel_cities, sel_districts, avg_val, history_df, all_cities, df)

if __name__ == "__main__":
    main()