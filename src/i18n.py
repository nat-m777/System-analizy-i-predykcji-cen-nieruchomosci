import streamlit as st
import pandas as pd
from src.utils import get_db, clean_df
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
        "welcome_msg": "Wybierz moduł z menu po lewej stronie, aby rozpocząć pracę.",
        "dash_title": "📊 Przegląd Rynku Nieruchomości",
        "dash_filters": "🔍 Filtry",
        "dash_select_city": "Wybierz Miasto",
        "dash_select_dist": "Wybierz Dzielnicę",
        "dash_avg_m2": "Śr. cena/m²",
        "dash_deals": "🔥 Okazje",
        "dash_premium": "💎 Premium",
        "dash_tab_anomalies": "🚩 Anomalie",
        "dash_tab_history": "📜 Historia",
        "dash_no_anomalies": "Brak anomalii w wybranym obszarze.",
        "dash_export_bal": "📥 Eksportuj wyniki (zrównoważone)",
        "dash_top100_csv": "📥 Pobierz TOP 100 CSV",
        "dash_gen_pdf": "📄 Generuj raport PDF",
        "dash_download_pdf": "🔥 Pobierz gotowy PDF",
        "dash_preview": "📋 Podgląd danych",
        "dash_status_norm": "✅ W normie",
        "chart_price_dist": "Rozkład cen nieruchomości",
        "chart_area_price": "Zależność ceny od powierzchni",
        "chart_price_label": "Cena (PLN)",
        "chart_count_label": "Liczba ofert",
        "chart_rooms_label": "Liczba pokoi",
        "chart_prediction_title": "Przewidywana wartość rynkowa",
        "chart_median_area": "Mediana cen w okolicy",
        "error_pdf": "❌ Błąd podczas generowania raportu PDF.",
        "error_db": "❌ Błąd połączenia z bazą danych.",
        "success_valuation": "✅ Wycena została pomyślnie zapisana w historii.",
        "unit_pln_m2": "zł/m²",
        "pdf_date": "Data", 
        "pdf_value": "WARTOŚĆ",
        "duel_page_title": "Pojedynek: Statystyka vs ML",
        "duel_title": "⚖️ Statystyka vs Machine Learning",
        "duel_desc": "Sprawdź, jak różnią się wyniki tradycyjnej analizy średnich od zaawansowanego modelu predykcyjnego.",
        "duel_params_header": "Parametry nieruchomości",
        "duel_stat_val": "Wycena Statystyczna",
        "duel_stat_cap": "Oparta na średniej cenie m² w lokalizacji",
        "duel_ml_val": "Wycena Machine Learning",
        "duel_ml_cap": "Oparta na modelu Random Forest (wiele cech)",
        "duel_diff_label": "Różnica metod",
        "duel_higher": "📈 ML wycenia wyżej",
        "duel_lower": "📉 ML wycenia niżej",
        "duel_method_col": "Metoda",
        "duel_price_col": "Cena [PLN]",
        "duel_chart_title": "Porównanie kwotowe metod wyceny",
        "duel_expander_title": "🧐 Dlaczego wyniki się różnią?",
        "duel_explanation": """
        **Statystyka (Średnia):** Bierze pod uwagę tylko cenę za metr w danym mieście/dzielnicy. Nie uwzględnia, czy mieszkanie ma 1 czy 5 pokoi w specyficzny sposób.
        **Machine Learning:** Analizuje nieliniowe zależności. Model 'nauczył się', że np. w tej konkretnej dzielnicy małe mieszkania dwupokojowe są warte znacznie więcej niż wynikałoby to tylko ze średniej ceny metra.
        """,
        "duel_no_model": "⚠️ Model ML nie jest gotowy lub brak danych dla tej lokalizacji.",
        "ml_too_little_data": "❌ Zbyt mało danych do trenowania (wymagane min. 10 ofert).",
        "ml_train_success": "✅ Model ML został zaktualizowany pomyślnie!", 
        "ml_page_title": "Inteligentna Wycena (Machine Learning)",
        "ml_manage_model": "Zarządzanie modelem",
        "ml_train_btn": "🔄 Wytrenuj model na danych",
        "ml_calc_btn": "💰 Oblicz cenę przez AI",
        "ml_last_result": "Ostatni wynik analizy",
        "pdf_title_ml": "RAPORT INTELIGENTNEJ WYCENY ML",
        "result_msg_short": "Sugerowana wartość",
        "tab_cities": "Ranking TOP 6 Miast",
        "comp_desc": "Porównaj średnie ceny mieszkań dla **TOP 6** miast w Polsce.",
        "comp_chart_avg": "Porównanie Średniej Ceny za m²",
        "comp_table_header": "Zestawienie Rankingowe",
        "dash_filters": "Filtry Rankingu",
        "dash_select_city": "Miasto",
        "dash_avg_m2": "Śr. cena za m²",
        "metric_offers": "Liczba ofert",
        "area_label": "Metraż (m²)",
        "rooms_label": "Liczba pokoi",
        "no_data": "⚠️ Brak danych spełniających wybrane kryteria.",
        "error_db": "Błąd sesji lub bazy danych. Zaloguj się ponownie.",
        "scraper_title": "Pobieranie danych z Otodom",
        "auto_refresh_msg": "Minęło 5 minut. Czy chcesz ponownie pobrać dane?",
        "yes_btn": "Tak, pobierz",
        "no_btn": "Nie teraz",
        "pages_label": "Liczba stron na dzielnicę",
        "run_scraper_btn": "🚀 Uruchom pobieranie",
        "error_no_districts": "Wybierz przynajmniej jedną dzielnicę!",
        "scraping_msg": "Pobieranie danych",
        "scrape_success": "✅ Zapisano {count} ofert dla użytkownika.",
        "settings_header": "Ustawienia",
        "toggle_auto_refresh": "Autoodświeżanie (5 min)",
        "db_mgmt_header": "Zarządzanie bazą",
        "delete_warning": "Uwaga: Usuniesz tylko SWOJE dane.",
        "confirm_label": "Potwierdzam chęć usunięcia",
        "delete_btn": "🗑️ Wyczyść moje oferty",
        "deleted_msg": "Wyczyszczono pomyślnie!",
        "error_no_results": "Nie pobrano żadnych danych.",
        "error_empty_data": "Błąd: Dane są puste po oczyszczeniu."
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
        "welcome_msg": "Select a module from the menu on the left to start working.",
        "dash_title": "📊 Real Estate Market Overview",
        "dash_filters": "🔍 Filters",
        "dash_select_city": "Select City",
        "dash_select_dist": "Select District",
        "dash_avg_m2": "Avg price/m²",
        "dash_deals": "🔥 Hot Deals",
        "dash_premium": "💎 Premium",
        "dash_tab_anomalies": "🚩 Anomalies",
        "dash_tab_history": "📜 History",
        "dash_no_anomalies": "No anomalies found in the selected area.",
        "dash_export_bal": "📥 Export results (balanced)",
        "dash_top100_csv": "📥 Download TOP 100 CSV",
        "dash_gen_pdf": "📄 Generate PDF Report",
        "dash_download_pdf": "🔥 Download PDF Report",
        "dash_preview": "📋 Data Preview",
        "dash_status_norm": "✅ Normal",
        "chart_price_dist": "Property Price Distribution",
        "chart_area_price": "Price vs. Area Relationship",
        "chart_price_label": "Price (PLN)",
        "chart_count_label": "Offer Count",
        "chart_rooms_label": "Rooms",
        "chart_prediction_title": "Estimated Market Value",
        "chart_median_area": "Median price in area",
        "error_pdf": "❌ Error generating PDF report.",
        "error_db": "❌ Database connection error.",
        "success_valuation": "✅ Valuation successfully saved in history.",
        "unit_pln_m2": "PLN/sqm",
        "chart_prediction_title": "Estimated Market Value",
        "chart_median_area": "Median price in the area",
        "pdf_date": "Date", 
        "pdf_value": "VALUE",
        "duel_page_title": "Duel: Stats vs ML",
        "duel_title": "⚖️ Statistics vs Machine Learning",
        "duel_desc": "Compare results from traditional average-based analysis vs a predictive machine learning model.",
        "duel_params_header": "Property Parameters",
        "duel_stat_val": "Statistical Valuation",
        "duel_stat_cap": "Based on average price per sqm in location",
        "duel_ml_val": "Machine Learning Valuation",
        "duel_ml_cap": "Based on Random Forest model (multi-feature)",
        "duel_diff_label": "Method Difference",
        "duel_higher": "📈 ML values higher",
        "duel_lower": "📉 ML values lower",
        "duel_method_col": "Method",
        "duel_price_col": "Price [PLN]",
        "duel_chart_title": "Value Comparison by Method",
        "duel_expander_title": "🧐 Why are the results different?",
        "duel_explanation": """
        **Statistics (Average):** Only considers the price per sqm in a given city/district. It doesn't nuancedly account for the specific room count.
        **Machine Learning:** Analyzes non-linear relationships. The model has 'learned' that, for example, in this specific district, small 2-room apartments are worth much more than the simple average price per sqm would suggest.
        """,
        "duel_no_model": "⚠️ ML model is not ready or data for this location is missing.",
        "ml_too_little_data": "❌ Not enough data to train (min. 10 offers required).",
        "ml_train_success": "✅ ML Model trained and updated successfully!",
        "ml_page_title": "Smart Valuation (Machine Learning)",
        "ml_manage_model": "Model Management",
        "ml_train_btn": "🔄 Train model on data",
        "ml_calc_btn": "💰 Calculate price via AI",
        "ml_last_result": "Latest analysis result",
        "pdf_title_ml": "ML SMART VALUATION REPORT",
        "result_msg_short": "Suggested value",
        "tab_cities": "TOP 6 Cities Ranking",
        "comp_desc": "Compare average apartment prices for the **TOP 6** cities in Poland.",
        "comp_chart_avg": "Average Price per sqm Comparison",
        "comp_table_header": "Ranking Summary Table",
        "dash_filters": "Ranking Filters",
        "dash_select_city": "City",
        "dash_avg_m2": "Avg price per sqm",
        "metric_offers": "Number of Offers",
        "area_label": "Area (sqm)",
        "rooms_label": "Number of rooms",
        "no_data": "⚠️ No data found for the selected criteria.",
        "error_db": "Session or database error. Please log in again.",
        "scraper_title": "Otodom Data Scraper",
        "auto_refresh_msg": "5 minutes have passed. Do you want to refresh the data?",
        "yes_btn": "Yes, scrape now",
        "no_btn": "Not now",
        "pages_label": "Pages per district",
        "run_scraper_btn": "🚀 Start Scraper",
        "error_no_districts": "Please select at least one district!",
        "scraping_msg": "Scraping data",
        "scrape_success": "✅ Saved {count} offers for the user.",
        "settings_header": "Settings",
        "toggle_auto_refresh": "Auto-refresh (5 min)",
        "db_mgmt_header": "Database Management",
        "delete_warning": "Warning: Only YOUR data will be deleted.",
        "confirm_label": "I confirm deletion",
        "delete_btn": "🗑️ Clear my offers",
        "deleted_msg": "Cleared successfully!",
        "error_no_results": "No data was scraped.",
        "error_empty_data": "Error: Data is empty after cleaning."
        
    }
}
# --- 2. KONFIGURACJA STRONY I INICJALIZACJA ---

st.set_page_config(page_title="Valuation App", layout="wide")
check_auth()

if 'lang' not in st.session_state:
    st.session_state.lang = "PL"

if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

# Sidebar do wyboru języka
with st.sidebar:
    st.session_state.lang = st.radio("Language / Język", options=["PL", "EN"], 
                                     index=0 if st.session_state.lang == "PL" else 1)

T = LANGUAGES[st.session_state.lang]

# --- 3. FUNKCJA GŁÓWNA ---

def main():
    # Import wykresów wewnątrz funkcji (uniknięcie Circular Import)
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

    # Kontener formularza wyceny
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

    # --- WYŚWIETLANIE WYNIKÓW ---
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=f"{int(val['price']):,}"))

    # --- STATYSTYKI DOLNE ---
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