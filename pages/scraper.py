import streamlit as st
import pandas as pd
import time
from src.utils.database import get_db
from src.utils.data import clean_df
from src.scraper.otodom import OtodomScraper
from src.auth import check_auth, delete_user_offers
from src.lang import get_text

# =========================================================
# 1. KONFIGURACJA STRONY
# =========================================================
T = get_text()

st.set_page_config(
    page_title=f"Scraper - {T.get('page_title', 'Valuation')}", 
    layout="wide"
)

# =========================================================
# 2. LOGIKA AUTOMATYZACJI I FRAGMENTY
# =========================================================

@st.dialog("🔄 automation_dialog_title")
def ask_for_scrape():
    """Wyświetla okno dialogowe z zapytaniem o ponowne pobieranie."""
    st.write(T.get("auto_refresh_msg", "Minęło 5 minut. Czy chcesz ponownie pobrać dane?"))
    col1, col2 = st.columns(2)
    with col1:
        if st.button(T.get("yes_btn", "Tak"), type="primary"):
            st.session_state["trigger_scrape"] = True
            st.rerun()
    with col2:
        if st.button(T.get("no_btn", "Nie")):
            st.rerun()

@st.fragment(run_every="5m")
def automation_timer():
    """Fragment odświeżany co 5 minut w tle."""
    st.session_state["timer_ping"] = time.time()
    
    current_time = time.time()
    # Sprawdzamy czy automatyzacja jest włączona
    if st.session_state.get("auto_refresh_enabled", False):
        last_check = st.session_state.get("last_check_time", 0)
        if current_time - last_check > 300:
            st.session_state["last_check_time"] = current_time
            ask_for_scrape()

# =========================================================
# 3. KONFIGURACJA I KOMPONENTY WEJŚCIOWE
# =========================================================

def get_city_config():
    return {
        "Warszawa": ["bemowo", "bialoleka", "bielany", "mokotow", "ochota", "praga-poludnie", "praga-polnoc", "rembertow", "srodmiescie", "targowek", "ursus", "ursynow", "wawer", "wesola", "wilanow", "wlochy", "wola", "zoliborz"],
        "Krakow": ["stare-miasto", "grzegorzki", "pradnik-czerwony", "pradnik-bialy", "krowodrza", "bronowice", "zwierzyniec", "debniki", "lagiewniki-borek-falecki", "swoszowice", "podgorze-duchackie", "biezanow-prokocim", "podgorze", "czyzyny", "mistrzejowice", "bienczyce", "nowa-huta", "wzgorza-krzeslawickie"],
        "Wroclaw": ["stare-miasto", "srodmiescie", "krzyki", "fabryczna", "psie-pole"],
        "Gdansk": ["aniolki", "brzezno", "chelm", "jasien", "jelitkowo", "kokoszki", "letnica", "matarnia", "mlyniska", "nowy-port", "oliwa", "olszynka", "orunia", "osowa", "piecki-migowo", "przerobka", "przymorze", "rudniki", "siedlce", "stogi", "strzyza", "suchanino", "srodmiescie", "wrzeszcz", "zaspa", "zabianka"],
        "Poznan": ["grunwald", "jezyce", "nowe-miasto", "stare-miasto", "wilda"],
        "Lodz": ["baluty", "gorna", "polesie", "srodmiescie", "widzew"]
    }

def render_scraper_form(config):
    """Renderuje formularz wyboru parametrów scrapowania."""
    col1, col2 = st.columns(2)
    with col1:
        city = st.selectbox(T.get("city_label", "Miasto"), list(config.keys()), key="sel_city")
    with col2:
        districts = st.multiselect(
            T.get("dist_label", "Dzielnice"), 
            options=config[city], 
            default=config[city][:3],
            key="sel_dist"
        )
    pages = st.slider(T.get("pages_label", "Liczba stron"), 1, 20, 3)
    return city, districts, pages

# =========================================================
# 4. PROCES POBIERANIA DANYCH
# =========================================================

def execute_scraping(city, districts, pages):
    """Główna pętla scrapująca dane."""
    db = get_db()
    scraper = OtodomScraper()
    username = st.session_state.get('username')
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_data = []
    
    for i, dist in enumerate(districts):
        status_text.text(f"{T.get('scraping_msg', 'Pobieranie')}: {city} - {dist}...")
        try:
            df_dist = scraper.fetch_data(city, max_pages=pages, selected_districts=[dist])
            if df_dist is not None and not df_dist.empty:
                total_data.append(df_dist)
        except Exception as e:
            st.warning(f"Error {dist}: {e}")
        progress_bar.progress((i + 1) / len(districts))

    if total_data:
        final_df = pd.concat(total_data, ignore_index=True)
        final_df = clean_df(final_df)
        
        if not final_df.empty:
            # Zapis do bazy (na oryginalnym final_df bez kolumny Lp.)
            final_df['owner'] = username
            db.insert_offers(final_df, username)
            
            st.success(T.get("scrape_success", "Zapisano!").format(count=len(final_df)))
            st.balloons()
            
            # Podgląd (na kopii z dodaną kolumną Lp.)
            with st.expander(T.get("preview_header", "Podgląd")):
                preview_df = final_df.copy()
                preview_df.insert(0, "Lp.", range(1, len(preview_df) + 1))       
                st.dataframe(preview_df, hide_index=True, use_container_width=True)
        else:
            st.error(T.get("error_empty_data", "Błąd po czyszczeniu."))
    else:
        st.error(T.get("error_no_results", "Nie pobrano danych."))
# =========================================================
# 5. SIDEBAR - ZARZĄDZANIE
# =========================================================

def render_sidebar_management():
    """Zarządzanie bazą i ustawieniami w panelu bocznym."""
    st.sidebar.divider()
    st.sidebar.subheader(T.get("settings_header", "⚙️ Ustawienia"))

    st.session_state["auto_refresh_enabled"] = st.sidebar.toggle(
        T.get("toggle_auto_refresh", "Autoodświeżanie"), 
        value=st.session_state.get("auto_refresh_enabled", True)
    )

    with st.sidebar.expander(T.get("db_mgmt_header", "⚠️ Zarządzanie bazą")):
        st.warning(T.get("delete_warning", "Usuniesz tylko SWOJE dane."))
        confirm_delete = st.checkbox(T.get("confirm_label", "Potwierdzam"))
        
        if st.button(T.get("delete_btn", "🗑️ Wyczyść"), disabled=not confirm_delete, type="primary"):
            delete_user_offers(st.session_state['username'])
            st.success(T.get("deleted_msg", "Wyczyszczono!"))
            time.sleep(1)
            st.rerun()

# =========================================================
# 6. GŁÓWNA FUNKCJA STERUJĄCA
# =========================================================

def main():
    check_auth()
    
    # Inicjalizacja stanów sesji
    if "trigger_scrape" not in st.session_state:
        st.session_state["trigger_scrape"] = False
    if "last_check_time" not in st.session_state:
        st.session_state["last_check_time"] = time.time()

    # Uruchomienie fragmentu timera
    automation_timer()

    st.title(f"🕵️ {T.get('scraper_title', 'Pobieranie danych')}")

    # UI i Parametry
    config = get_city_config()
    city, districts, pages = render_scraper_form(config)
    
    render_sidebar_management()

    # Logika startu
    manual_trigger = st.button(T.get("run_scraper_btn", "🚀 Uruchom"), use_container_width=True)

    if manual_trigger or st.session_state["trigger_scrape"]:
        st.session_state["trigger_scrape"] = False
        if not districts:
            st.error(T.get("error_no_districts", "Wybierz dzielnicę!"))
        else:
            execute_scraping(city, districts, pages)

if __name__ == "__main__":
    main()