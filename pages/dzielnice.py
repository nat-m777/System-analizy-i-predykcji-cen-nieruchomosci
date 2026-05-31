import streamlit as st
import pandas as pd
import plotly.express as px

# Importy ze struktury src
from src.utils.database import get_db
from src.utils.data import clean_df
from src.auth import check_auth, save_search, get_search_history
from src.lang import get_text

# Zabezpieczenie dostępu (użytkownik musi być zalogowany)
check_auth()
T = get_text()
username = st.session_state.get('username', 'User')

def create_top6_district_chart(df, selected_city):
    """
    Generuje dedykowany wykres słupkowy średnich cen za m² 
    dla dzielnic w wybranym mieście z TOP 6.
    """
    # Dynamiczna waluta i etykiety osi na podstawie języka
    currency = "USD" if "welcome" in T.get("welcome_msg", "").lower() else "EUR" if "welcome" in T.get("welcome_msg", "").lower() else "zł"
    if currency != "zł":
        currency = "PLN"
        
    label_district = T.get("dist_label", "Dzielnica")
    label_avg_price = f"{T.get('dash_avg_m2', 'Średnia cena')} ({currency}/m²)"

    if df is None or df.empty or 'district' not in df.columns:
        st.warning(T.get("top6_err_no_district_col", "⚠️ Brak kolumny 'district' (dzielnica) w przetworzonych danych."))
        return None

    # Kopia danych i pełą normalizacja tekstowa
    df_clean = df.copy()
    df_clean['city_lower'] = df_clean['city'].astype(str).str.lower().str.strip()
    target_city = str(selected_city).lower().strip()

    # Filtrowanie rekordów dla wskazanego miasta posiadających cenę za m²
    city_df = df_clean[
        (df_clean['city_lower'] == target_city) & 
        (df_clean['price_per_m2'].notna())
    ]

    if city_df.empty:
        st.info(f"{T.get('top6_info_no_offers', 'ℹ️ Brak dostępnych ofert z ceną za m² dla miasta:')} {selected_city}")
        return None

    # Obliczanie średniej ceny za m² w podziale na dzielnice
    stats = city_df.groupby('district')['price_per_m2'].mean().reset_index()
    stats = stats.rename(columns={'district': label_district, 'price_per_m2': label_avg_price})

    # Oczyszczanie z wartości pustych oraz placeholderów systemowych
    stats['Dzielnica_clean'] = stats[label_district].astype(str).str.lower().str.strip()
    stats = stats[
        (stats['Dzielnica_clean'] != "") & 
        (stats['Dzielnica_clean'] != "none") &
        (stats['Dzielnica_clean'] != "nan") &
        (stats['Dzielnica_clean'] != "nieznana") &
        (stats['Dzielnica_clean'] != "unknown")
    ]

    # Sortowanie rosnąco według cen
    stats = stats.sort_values(by=label_avg_price, ascending=True)

    if stats.empty:
        st.warning(f"{T.get('top6_warn_empty_districts', '⚠️ Wszystkie znalezione dzielnice dla miasta {city} to wartości puste lub nieznane.').format(city=selected_city)}")
        return None

    # Wykres słupkowy poziomy
    fig = px.bar(
        stats,
        x=label_avg_price,
        y=label_district,
        orientation='h',
        title=f"🏙️ {T.get('top6_chart_title', 'Średnia cena za m² według dzielnic w mieście:')} {selected_city}",
        labels={label_avg_price: label_avg_price, label_district: label_district},
        color=label_avg_price,
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        showlegend=False, 
        height=400 + (len(stats) * 20),
        xaxis_title=label_avg_price,
        yaxis_title=label_district
    )
    return fig

def main():
    st.title(f"🏙️ {T.get('top6_page_title', 'Analiza Dzielnic TOP 6')}")
    st.markdown(T.get("top6_page_desc", "Dedykowany moduł porównania średnich cen nieruchomości za m² w obrębie dzielnic największych polskich miast."))
    st.divider()

    # 1. Pobranie danych z bazy PostgreSQL
    db = get_db()
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.error(T.get("no_data", "Brak danych w bazie."))
        return

    # --- OCZYSZCZANIE NAZW MIAST  ---
    df['city'] = df['city'].astype(str).str.replace(r'[\r\n\t]+', '', regex=True).str.strip()
    
    # Definicja zmiennej na samym początku procesu oczyszczania danych
    raw_cities_in_db = list(df['city'].unique())
    
    def normalize_text(text_val):
        replacements = {'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'}
        val = str(text_val).lower().strip()
        for k, v in replacements.items():
            val = val.replace(k, v)
        return val

    db_cities_normalized = set(df['city'].apply(normalize_text).unique())

    # 2. Definicja docelowej grupy miast TOP 6
    top_6_cities = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Łódź"]

    # Wybór miast, które są w TOP 6 ORAZ fizycznie posiadają rekordy w bazie
    available_top6 = sorted([
        city for city in top_6_cities 
        if normalize_text(city) in db_cities_normalized
    ])

    if not available_top6:
        st.warning(T.get("top6_warn_no_top6_data", "⚠️ W bazie danych nie znaleziono żadnych ofert powiązanych z miastami TOP 6."))
        st.info(f"{T.get('top6_info_current_cities', 'Twoja baza zawiera obecnie miasta:')} {raw_cities_in_db}")
        return

    # --- OBSŁUGA STANU SESJI (STATE MANAGEMENT) ---
    if "top6_selected_city" not in st.session_state:
        st.session_state["top6_selected_city"] = available_top6[0]

    try:
        current_index = available_top6.index(st.session_state["top6_selected_city"])
    except ValueError:
        current_index = 0

    # 3. Dropdown wyboru miasta sprzężony ze st.session_state
    selected_city = st.selectbox(
        T.get("top6_select_city_label", "Wybierz miasto do analizy dzielnicowej:"), 
        options=available_top6,
        index=current_index
    )
    st.session_state["top6_selected_city"] = selected_city

    # --- PANEL BOCZNY: ZAPIS FILTRÓW (ODSEPAROWANY - TAG [TOP6]) ---
    st.sidebar.markdown("---")
    if st.sidebar.button(f"💾 {T.get('dash_save_search_btn', 'Zapisz to wyszukiwanie')}", use_container_width=True):
        try:
            # Dodajemy tag [TOP6] na początku pola z opisem szczegółów
            all_districts_text = "All districts" if "welcome" in T.get("welcome_msg", "").lower() else "Wszystkie dzielnice"
            save_search(username, selected_city, f"[TOP6] {all_districts_text}")
            st.toast(f"✅ {T.get('top6_toast_saved', 'Zapisano analizę dla miasta')} {selected_city}!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"{T.get('dash_err_save', 'Nie udało się zapisać')}: {e}")

    # Mapowanie wybranego miasta na wersję surową z bazy (w razie problemów z kodowaniem znaków)
    matched_db_city = selected_city
    for raw_c in raw_cities_in_db:
        if normalize_text(raw_c) == normalize_text(selected_city):
            matched_db_city = raw_c
            break

    current_city_data = df[df['city'] == matched_db_city]

    # 4. Renderowanie wykresu analitycznego
    st.subheader(f"📊 {T.get('top6_results_header', 'Wyniki dla miasta:')} {selected_city}")
    
    fig = create_top6_district_chart(df, matched_db_city)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander(f"🔍 {T.get('top6_expander_table', 'Zobacz zestawienie tabelaryczne')}"):
            city_df_clean = current_city_data[
                (current_city_data['district'].astype(str).str.lower() != 'nieznana') & 
                (current_city_data['district'].astype(str).str.lower() != 'unknown') & 
                (current_city_data['price_per_m2'].notna())
            ]
            if not city_df_clean.empty:
                table_stats = city_df_clean.groupby('district').agg(
                    srednia_cena_m2=('price_per_m2', 'mean'),
                    liczba_ofert=('id', 'count')
                ).reset_index().sort_values(by='srednia_cena_m2', ascending=False)
                
                # Formatowanie walutowe i etykiety tabeli
                currency_suffix = "PLN/m²" if "welcome" in T.get("welcome_msg", "").lower() else "zł"
                table_stats.columns = [
                    T.get("dist_label", "Dzielnica"), 
                    f"{T.get('dash_avg_m2', 'Śr. cena')} ({currency_suffix})", 
                    T.get("top6_table_offers_count", "Liczba dostępnych ofert")
                ]
                st.dataframe(
                    table_stats.style.format({f"{T.get('dash_avg_m2', 'Śr. cena')} ({currency_suffix})": f"{{:.2f}} {currency_suffix}"}), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.write(T.get("top6_no_detailed_data", "Brak szczegółowych danych o dzielnicach dla tego miasta."))
    else:
        st.warning(T.get("top6_err_chart_failed", "Nie można wygenerować wykresu słupkowego (zbyt mało danych szczegółowych o dzielnicach w bazie)."))

    # --- INTERAKTYWNA HISTORIA WYSZUKIWAŃ (ODSEPAROWANA DLA TOP 6) ---
    st.divider()
    st.subheader(f"🕒 {T.get('top6_history_header', 'Twoja historia wyszukiwań dla TOP 6')}")
    
    history_raw = get_search_history(username)
    
    if history_raw:
        history_df = pd.DataFrame(history_raw)
        
        if not history_df.empty and "Dzielnice" in history_df.columns:
            history_df = history_df[history_df["Dzielnice"].astype(str).str.contains(r"\[TOP6\]", na=False)]
            
        recent_searches = history_df.head(10)
        
        if not recent_searches.empty:
            col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 4, 2])
            with col_h1: st.markdown(f"**{T.get('pdf_date', 'Data')}**")
            with col_h2: st.markdown(f"**{T.get('city_label', 'Miasto')}**")
            with col_h3: st.markdown(f"**{T.get('top6_hist_details_label', 'Szczegóły')}**")
            with col_h4: st.markdown(f"**{T.get('dash_hist_action', 'Akcja')}**")
            st.markdown("---")
            
            for idx, row in recent_searches.iterrows():
                saved_date = row.get("Data", "")
                saved_city_raw = row.get("Miasta", "")
                saved_details = row.get("Dzielnice", "")
                
                display_details = str(saved_details).replace("[TOP6] ", "")
                if "wszystkie dzielnice" in display_details.lower():
                    display_details = T.get("top6_hist_all_districts", "Wszystkie dzielnice")
                    
                first_city_match = str(saved_city_raw).split(",")[0].replace("Miasta:", "").strip().capitalize()
                
                c1, c2, c3, c4 = st.columns([2, 2, 4, 2])
                with c1: st.write(saved_date)
                with c2: st.write(saved_city_raw)
                with c3: st.caption(display_details)
                with c4:
                    if first_city_match in available_top6:
                        if st.button(T.get("dash_load_btn", "Wczytaj 🔄"), key=f"load_btn_{idx}", use_container_width=True):
                            st.session_state["top6_selected_city"] = first_city_match
                            st.toast(f"🔄 {T.get('top6_toast_loaded', 'Załadowano filtry dla:')} {first_city_match}")
                            st.rerun()
                    else:
                        st.caption(T.get("top6_hist_generic_menu", "Ogólne menu"))
        else:
            st.info(T.get("top6_no_saved_searches", "Brak zapisanych wyszukiwań dla modułu TOP 6."))
    else:
        st.info(T.get("top6_no_history_at_all", "Brak historii wyszukiwań w historii dla Twojego profilu."))

if __name__ == "__main__":
    main()