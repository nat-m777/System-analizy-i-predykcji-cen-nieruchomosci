import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Importy z Twojej struktury src - moduły odpowiedzialne za logikę, bazę i UI
from src.utils.database import get_db
from src.utils.data import clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
from src.auth import save_search, check_auth, get_search_history, init_auth_db
from src.lang import get_text
from src.utils.export import generate_valuation_pdf

# --- 1. ZABEZPIECZENIE I JĘZYK ---
# Weryfikacja czy użytkownik jest zalogowany przed załadowaniem reszty skryptu
check_auth() 
T = get_text() # Pobranie słownika tłumaczeń (i18n)
username = st.session_state.get('username', 'User')

def get_balanced_top_n(df, n, cities):
    """
    Pomocnicza funkcja do wyboru zrównoważonych ofert do raportu.
    Stara się pobrać podobną liczbę najtańszych ofert z każdego wybranego miasta.

    Args:
        df (pd.DataFrame): Zbiór danych z ofertami.
        n (int): Całkowita liczba rekordów do zwrócenia.
        cities (list): Lista miast, które mają być uwzględnione.

    Returns:
        pd.DataFrame: Przefiltrowany zbiór danych.
    """
    if not cities or df.empty: 
        return df.sort_values('price_per_m2').head(n)
    
    df_clean = df.dropna(subset=['price', 'price_per_m2'])
    per_city = n // len(cities) # Ile ofert przypada na jedno miasto
    remainder = n % len(cities)  # Reszta do rozdzielenia między pierwsze miasta
    results = []
    
    for i, city in enumerate(sorted(cities)):
        limit = per_city + (1 if i < remainder else 0)
        if limit > 0:
            # Pobieramy najtańsze oferty (pod względem m2) dla danego miasta
            city_top = df_clean[df_clean['city'] == city].sort_values('price_per_m2').head(limit)
            results.append(city_top)
            
    return pd.concat(results) if results else pd.DataFrame()

def mark_outliers(group):
    """
    Oznacza okazje i oferty premium na podstawie rozkładu IQR (Interquartile Range) wewnątrz grupy.
    
    Args:
        group (pd.DataFrame): Grupa danych (zazwyczaj per dzielnica).

    Returns:
        pd.DataFrame: Grupa z dodaną kolumną 'status'.
    """
    status_norm = T.get("dash_status_norm", "✅ W normie")
    status_deal = T.get("dash_deals", "🔥 Okazja")
    status_premium = T.get("dash_premium", "💎 Premium")
    
    # Do rzetelnej analizy statystycznej potrzebujemy co najmniej 5 ofert
    if len(group) < 5 or group['price_per_m2'].isnull().all(): 
        return group.assign(status=status_norm)
        
    q1, q3 = group['price_per_m2'].quantile([0.25, 0.75])
    iqr = q3 - q1
    
    group['status'] = status_norm
    # Logika wykrywania anomalii cenowych
    group.loc[group['price_per_m2'] < (q1 - 1.5 * iqr), 'status'] = status_deal
    group.loc[group['price_per_m2'] > (q3 + 1.5 * iqr), 'status'] = status_premium
    return group

def render_dashboard_ui(df, sel_cities, sel_districts, avg_val, history_df):
    """
    Główny interfejs Dashboardu renderujący metryki, wykresy i opcje eksportu.
    
    Args:
        df (pd.DataFrame): Przefiltrowane dane.
        sel_cities (list): Lista wybranych miast.
        sel_districts (list): Lista wybranych dzielnic.
        avg_val (float): Średnia cena za m2.
        history_df (pd.DataFrame): Historia wyszukiwań użytkownika.
    """
    st.title(f"Witaj {username}! 👋")
    st.info(T.get("welcome_msg", "Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę."))
    
    st.divider()
    st.subheader(T.get("dash_title", "Przegląd Rynku"))
    
    # Obliczenie globalnej średniej ceny całkowitej dla aktualnego widoku
    avg_total_price = df['price'].mean() if 'price' in df.columns else 0
    
    # --- SEKCOJA METRYK ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(T.get("metric_offers", "Oferty"), len(df))
    m2.metric(T.get("dash_avg_m2", "Śr. cena m²"), f"{round(avg_val if pd.notnull(avg_val) else 0, 0)} zł")
    m3.metric(T.get("dash_avg_total", "Śr. cena całkowita"), 
             f"{int(avg_total_price):,}".replace(",", " ") + " zł" if pd.notnull(avg_total_price) else "0 zł")
    
    # Zliczanie okazji i ofert premium na podstawie wcześniej nadanych statusów
    deals_count = len(df[df['status'].str.contains("Okazja|Deal", na=False)])
    m4.metric(T.get("dash_deals", "Okazje"), deals_count)
    
    premium_count = len(df[df['status'].str.contains("Premium", na=False)])
    m5.metric(T.get("dash_premium", "Premium"), premium_count)

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
            # Wywołanie zewnętrznych funkcji generujących wykresy Plotly
            st.plotly_chart(create_price_histogram(df_charts), use_container_width=True)
            fig_area_price = create_area_vs_price_chart(df_charts)
            if fig_area_price is not None:
                st.plotly_chart(fig_area_price, use_container_width=True)
            else:
                st.warning("⚠️ Brak wystarczających danych do wygenerowania wykresu ceny od powierzchni.")
        else:
            st.warning(T.get("no_data_charts", "Zbyt mało danych do generowania wykresów."))

    with tabs[1]:
        st.write(T.get("anomalies_desc", "Oferty odbiegające cenowo od średniej w danej dzielnicy:"))
        # Wyświetlenie tylko tych ofert, które nie są "W normie"
        st.dataframe(
            df[df['status'] != T.get("dash_status_norm", "✅ W normie")].sort_values("price_per_m2"),
            use_container_width=True
        )

    with tabs[2]:
        st.write(f"### {T.get('history_title', 'Twoje ostatnie zapisane wyszukiwania')}")
        if history_df is not None and not history_df.empty:
            st.table(history_df.head(10))
        else:
            st.info(T.get("no_history", "Brak historii wyszukiwań."))

    with tabs[3]:
        # Surowy podgląd tabelaryczny
        st.dataframe(df.sort_values("price_per_m2", ascending=True), use_container_width=True)

    # --- EKSPORT DANYCH ---
    st.divider()
    st.subheader(T.get("dash_export_bal", "Eksport Wyników"))
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"**{T.get('export_csv_desc', 'TOP 100 Ofert (CSV)')}**")
        df_csv = get_balanced_top_n(df, 100, sel_cities)
        csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label=T.get("dash_top100_csv", "Pobierz CSV"), data=csv_data, 
                         file_name=f"export_{datetime.now().strftime('%Y%m%d')}.csv",
                         mime="text/csv", use_container_width=True)
        
    with c2:
        st.write(f"**{T.get('export_pdf_desc', 'Raport TOP 15 (PDF)')}**")
        # Przygotowanie parametrów tekstowych do wstrzyknięcia w szablon PDF
        pdf_params = {
            T.get("city_label", "Miasta"): ", ".join(sel_cities[:3]) + ("..." if len(sel_cities)>3 else ""),
            T.get("metric_offers", "Liczba ofert"): len(df),
            T.get("dash_avg_total", "Śr. cena"): f"{int(avg_total_price):,} zł".replace(",", " ")
        }
        # Generowanie PDF w pamięci i udostępnienie do pobrania
        # 1. Wywołujemy generator PDF i przechwytujemy wynik
        pdf_bytes = None
        try:
            # Upewnij się, że przekazujesz odpowiednie parametry do swojej funkcji
            pdf_bytes = generate_valuation_pdf(pdf_params, avg_val, T)
        except Exception as pdf_gen_err:
            st.error(f"Błąd krytyczny podczas generowania pliku: {pdf_gen_err}")

        # 2. PANCERNE ZABEZPIECZENIE: Przycisk renderuje się TYLKO, gdy bajty istnieją
        if pdf_bytes is not None:
            st.download_button(
                label=T.get("dash_download_pdf", "Pobierz Raport PDF"), 
                data=pdf_bytes,
                file_name="market_report.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )
        else:
            # Zamiast błędu Streamlita, użytkownik zobaczy czytelny komunikat systemowy
            st.error("❌ Przycisk pobierania jest niedostępny. Generator nie mógł utworzyć pliku PDF.")

def main():
    """
    Logika główna strony Dashboardu. Obsługuje pobieranie danych z DB, 
    filtrowanie w sidebarze oraz wywołanie renderowania UI.
    """
    init_auth_db()
    db = get_db()
    
    # 1. Pobieranie danych i historii z bazy
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw) # Oczyszczenie danych (typy, brakujące wartości)
    
    # Próba pobrania historii filtrów użytkownika
    try:
        history_raw = get_search_history(username)
        history_df = pd.DataFrame(history_raw) if history_raw else pd.DataFrame()
    except:
        history_df = pd.DataFrame()
    
    if df is None or df.empty:
        st.title(f"Witaj {username}! 👋")
        st.info(T.get("no_data", "Brak danych w bazie. Użyj Scrapera, aby pobrać pierwsze oferty."))
        return

    # Standaryzacja nazw kolumn dla spójności w UI
    df = df.rename(columns={"district": "Dzielnica"}) if "district" in df.columns else df
    
    # --- FILTRY W SIDEBARZE ---
    st.sidebar.header(T.get("dash_filters", "Filtry"))
    all_cities = sorted(df["city"].unique())
    sel_cities = st.sidebar.multiselect(T.get("dash_select_city", "Miasto"), all_cities, default=all_cities)
    
    # Dzielnice filtrujemy dynamicznie na podstawie wybranych miast
    df_t = df[df["city"].isin(sel_cities)]
    all_dists = sorted(df_t["Dzielnica"].unique())
    sel_districts = st.sidebar.multiselect(T.get("dash_select_dist", "Dzielnica"), all_dists, default=all_dists)
    
    # Akcja zapisu aktualnego stanu filtrów do bazy danych
    if st.sidebar.button(T.get("save_search", "Zapisz filtry")):
        save_search(username, sel_cities, sel_districts)
        st.toast("Zapisano!")

    # Aplikowanie finalnych filtrów na DataFrame
    df_f = df[df["city"].isin(sel_cities) & df["Dzielnica"].isin(sel_districts)].copy()
    
    if df_f.empty:
        st.warning(T.get("no_data_filters", "Brak danych dla wybranych filtrów."))
        return

    # Przeprowadzenie analizy statystycznej per dzielnica
    df_f = df_f.groupby('Dzielnica', group_keys=False).apply(mark_outliers)
    avg_val = df_f['price_per_m2'].mean()

    # Wywołanie głównego interfejsu
    render_dashboard_ui(df_f, sel_cities, sel_districts, avg_val, history_df)

if __name__ == "__main__":
    main()