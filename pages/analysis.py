import streamlit as st
import pandas as pd
from src.utils.database import get_db
from src.utils.data import clean_df
from src.utils.export import generate_valuation_pdf
from src.auth import check_auth
from src.lang import get_text
from src.utils.export import generate_valuation_pdf, prepare_csv

# --- 1. KONFIGURACJA I ZABEZPIECZENIE ---
# Weryfikacja sesji użytkownika (czy jest zalogowany)
check_auth()

# Pobranie tekstów interfejsu (i18n) na podstawie wybranego języka
T = get_text()

# Konfiguracja metadanych strony - musi być wywołana przed innymi elementami UI
st.set_page_config(page_title=T["page_title"], layout="wide")

# --- INICJALIZACJA STANU SESJI ---
# Zapobiega utracie wyników ostatniej wyceny po odświeżeniu interfejsu (rerun)
if 'last_valuation' not in st.session_state:
    st.session_state.last_valuation = None

def main():
    """
    Główna funkcja modułu wyceny.
    Obsługuje formularz wejściowy, obliczenia statystyczne oraz sekcję eksportu wyników.
    """
    # Import lokalny zapobiega problemom z zapętleniem importów (circular imports)
    from src.analysis.charts import show_price_prediction_logic
    
    st.title(T["title"])
    
    # Inicjalizacja połączenia z bazą i pobranie ofert przypisanych do użytkownika
    db = get_db()
    username = st.session_state.get('username')
    df_raw = db.get_all_offers(username) 
    df = clean_df(df_raw) # Oczyszczenie danych z duplikatów i błędnych wartości

    # Blokada modułu w przypadku braku danych źródłowych
    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    st.divider()
    st.subheader(T["calc_header"])

    # --- FORMULARZ WYCENY ---
    # Kontener grupujący pola wejściowe dla lepszej organizacji wizualnej
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            # Dynamiczne listy miast pobierane bezpośrednio z dostępnych ofert
            in_city = st.selectbox(T["city_label"], options=sorted(df["city"].unique()), key="city_select")
            in_area = st.number_input(T["area_label"], min_value=10, max_value=500, value=50)
        with col2:
            # Dynamiczne filtrowanie dzielnic na podstawie wybranego miasta
            available_districts = sorted(df[df["city"] == in_city]["district"].unique())
            in_dist = st.selectbox(T["dist_label"], options=available_districts, key="dist_select")
            in_rooms = st.slider(T["rooms_label"], 1, 10, 2)

        if st.button(T["calc_btn"], use_container_width=True):
            # --- LOGIKA WYCENY STATYSTYCZNEJ ---
            # 1. Filtrujemy bazę do konkretnej dzielnicy
            subset = df[(df['city'] == in_city) & (df['district'] == in_dist)].copy()
            
            # 2. Fallback: Jeśli dzielnica ma za mało danych, bierzemy średnią z całego miasta
            if subset.empty: 
                subset = df[df['city'] == in_city].copy()
            
            # 3. Obliczenie estymowanej ceny na podstawie średniej ceny za m2
            avg_m2 = subset['price_per_m2'].mean()
            price_est = (avg_m2 if pd.notna(avg_m2) else 0) * in_area

            # Zapisanie parametrów i wyniku do session_state, aby przetrwały interakcję
            st.session_state.last_valuation = {
                "city": in_city, 
                "district": in_dist, 
                "area": in_area, 
                "rooms": in_rooms, 
                "price": price_est,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            # Rejestracja aktywności w systemie analitycznym bazy danych
            db.update_stat(username, "valuation_requests_count")
            st.rerun()

    # --- SEKCJA WYNIKÓW I EKSPORTU ---
    # Wyświetlana tylko wtedy, gdy w tej sesji wykonano już co najmniej jedną kalkulację
    if st.session_state.last_valuation:
        val = st.session_state.last_valuation
        st.divider()
        
        # Sekcja wizualizacji: Wykresy kontekstowe (rozkład cen w okolicy)
        with st.expander(T["chart_expander"], expanded=True):
            show_price_prediction_logic(df, val['area'], val['city'], val['district'])

        # Prezentacja wyniku głównego w sformatowanej formie (np. 500 000 zł)
        formatted_price = f"{int(val['price']):,}".replace(',', ' ')
        st.success(T["result_msg"].format(city=val['city'], dist=val['district'], price=formatted_price))
        
        # --- PANEL EKSPORTU ---
        st.write(f"### 💾 {T.get('export_header', 'Eksport danych')}")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Generowanie surowych danych CSV dla arkuszy kalkulacyjnych
            csv_bytes = prepare_csv(val)
            st.download_button(
                label=T["download_csv"],
                data=csv_bytes,
                file_name=f"wycena_{val['city']}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with col_exp2:
            # Generowanie profesjonalnego raportu PDF (certyfikatu wyceny)
            # Mapowanie parametrów na etykiety językowe przed wysłaniem do generatora
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
    # Sekcja dla analityków - pokazuje surowe średnie i mediany dla wybranego regionu
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
    # Import datetime wewnątrz bloku name, aby uniknąć błędów przy ładowaniu skryptu jako moduł
    from datetime import datetime 
    main()