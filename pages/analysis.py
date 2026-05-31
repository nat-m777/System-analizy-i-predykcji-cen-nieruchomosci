import streamlit as st
import pandas as pd
from src.utils.database import get_db
from src.utils.data import clean_df
from src.utils.export import generate_valuation_pdf
from src.auth import check_auth
from src.lang import get_text
from src.utils.export import generate_valuation_pdf, prepare_csv

# --- 1. KONFIGURACJA I ZABEZPIECZENIE ---
check_auth()
T = get_text()

st.set_page_config(page_title=T["page_title"], layout="wide")

# --- INICJALIZACJA PARAMETRÓW W SESJI ---
if "val_city" not in st.session_state:
    st.session_state.val_city = None
if "val_area" not in st.session_state:
    st.session_state.val_area = 50
if "val_dist" not in st.session_state:
    st.session_state.val_dist = None
if "val_rooms" not in st.session_state:
    st.session_state.val_rooms = 2

def trigger_rerun():
    """Wymusza natychmiastowe przeładowanie skryptu przy zmianie dowolnego suwaka/pola."""
    st.rerun()

def main():
    """
    Główna funkcja modułu wyceny.
    Przelicza i odświeża widok automatycznie przy użyciu sterowania stanem sesji.
    """
    from src.analysis.charts import show_price_prediction_logic
    
    st.title(T["title"])
    
    db = get_db()
    username = st.session_state.get('username')
    df_raw = db.get_all_offers(username) 
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    # Ustawienie domyślnego miasta, jeśli sesja jest pusta
    unique_cities = sorted(df["city"].unique())
    if st.session_state.val_city not in unique_cities:
        st.session_state.val_city = unique_cities[0]

    st.divider()
    st.subheader(T["calc_header"])

    # --- FORMULARZ WEJŚCIOWY ZAKOTWICZONY W SESJI ---
    col1, col2 = st.columns(2)
    with col1:
        in_city = st.selectbox(
            T["city_label"], 
            options=unique_cities, 
            key="val_city", 
            on_change=trigger_rerun
        )
        in_area = st.number_input(
            T["area_label"], 
            min_value=1, 
            max_value=2000, 
            key="val_area", 
            on_change=trigger_rerun
        )
    with col2:
        available_districts = sorted(df[df["city"] == in_city]["district"].unique())
        
        # Bezpiecznik dla dzielnicy przy zmianie miasta
        if st.session_state.val_dist not in available_districts:
            st.session_state.val_dist = available_districts[0] if available_districts else ""

        in_dist = st.selectbox(
            T["dist_label"], 
            options=available_districts, 
            key="val_dist", 
            on_change=trigger_rerun
        )
        in_rooms = st.slider(
            T["rooms_label"], 
            min_value=1, 
            max_value=10, 
            key="val_rooms", 
            on_change=trigger_rerun
        )

    # --- LOGIKA AUTOMATYCZNEJ WYCENY W LOCIE ---
    # Filtrowanie rygorystyczne (Pokoje + Dzielnica + Miasto)
    subset = df[
        (df['city'] == in_city) & 
        (df['district'] == in_dist) & 
        (df['rooms'] == in_rooms)
    ].copy()
    
    # Bezpiecznik 1: Brak dokładnej liczby pokoi -> bierzemy całą dzielnicę
    if subset.empty or len(subset) < 2: 
        subset = df[(df['city'] == in_city) & (df['district'] == in_dist)].copy()
        
    # Bezpiecznik 2: Brak danych dla dzielnicy -> bierzemy całe miasto
    if subset.empty or len(subset) < 2: 
        subset = df[df['city'] == in_city].copy()

    # --- OBLICZENIE ŚREDNIEJ CENY ZA METR ---
    avg_m2 = subset['price_per_m2'].mean()
    current_calculated_price = (avg_m2 if pd.notna(avg_m2) else 0) * in_area

    # Diagnostyka matematyczna wyświetlana na ekranie
    st.info(f"🔍 **Diagnostyka:** Oferty: **{len(subset)}** szt. | Średnia cena m²: **{round(avg_m2, 2) if pd.notna(avg_m2) else 0} zł/m²**")

    # --- WALIDACJA METRAŻU ---
    if not subset.empty and 'area' in subset.columns:
        min_allowed_area = subset['area'].min()
        max_allowed_area = subset['area'].max()
    else:
        min_allowed_area = 10
        max_allowed_area = 500

    if in_area < min_allowed_area or in_area > max_allowed_area:
        is_en = "welcome" in T.get("welcome_msg", "").lower()
        if is_en:
            st.error(f"❌ Cannot perform calculation. Area must be between {min_allowed_area} m² and {max_allowed_area} m² for this location.")
        else:
            st.error(f"❌ Nie można rozpocząć obliczeń. Metraż dla tej lokalizacji musi mieścić się w przedziale od {min_allowed_area} m² do {max_allowed_area} m².")
        return

    # Zapis struktury do sesji (wymagany przez moduły eksportu PDF/CSV)
    val = {
        "city": in_city, 
        "district": in_dist, 
        "area": in_area, 
        "rooms": in_rooms, 
        "price": current_calculated_price,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.last_valuation = val

    # --- SEKCJA WYNIKÓW I EKSPORTU ---
    if current_calculated_price > 0:
        st.divider()
        
        # Zastosowanie unikalnego klucza (key) dla kontenera, opartego na cenie i pokojach,
        # uniemożliwia Streamlitowi zablokowanie (zbuforowanie) starego widoku HTML.
        with st.container(key=f"box_render_{in_rooms}_{int(current_calculated_price)}"):
            
            with st.expander(T["chart_expander"], expanded=True):
                show_price_prediction_logic(df, in_area, in_city, in_dist, in_rooms)
            
            # GŁÓWNA POPRAWKA: Formatowanie ceny odbywa się bezpośrednio na zmiennej `current_calculated_price`
            # wyliczonej w linii 97, całkowicie omijając pamięć podręczną sesji.
            formatted_price = f"{int(current_calculated_price):,}".replace(',', ' ')
            st.success(T["result_msg"].format(city=in_city, dist=in_dist, price=formatted_price))
            
            # --- PANEL EKSPORTU ---
            st.write(f"### 💾 {T.get('export_header', 'Eksport danych')}")
            col_exp1, col_exp2 = st.columns(2)
            
            with col_exp1:
                csv_bytes = prepare_csv(val)
                st.download_button(
                    label=T["download_csv"],
                    data=csv_bytes,
                    file_name=f"wycena_{in_city}.csv",
                    mime="text/csv",
                    key=f"csv_{in_rooms}_{int(current_calculated_price)}",
                    use_container_width=True
                )
                
            with col_exp2:
                pdf_params = {
                    T["city_label"]: in_city,
                    T["dist_label"]: in_dist,
                    T["area_label"]: f"{in_area} m²",
                    T["rooms_label"]: in_rooms
                }
                pdf_bytes = generate_valuation_pdf(pdf_params, current_calculated_price, T)
                if pdf_bytes:
                    st.download_button(
                        label=T["download_pdf"],
                        data=pdf_bytes,
                        file_name=f"certyfikat_{in_city}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{in_rooms}_{int(current_calculated_price)}",
                        use_container_width=True
                    )
    else:
        st.warning(f"⚠️ Nie można oszacować ceny. W bazie danych brakuje ofert dla lokalizacji: {in_city} ({in_dist}).")

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
    from datetime import datetime 
    main()