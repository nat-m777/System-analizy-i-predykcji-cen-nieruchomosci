import streamlit as st
import pandas as pd
import time
from src.utils import get_db, clean_df
from src.scraper.otodom import OtodomScraper
from src.auth import check_auth, delete_user_offers
from src.lang import get_text # Import funkcji pobierającej aktualny język

# 1. KONFIGURACJA STRONY
T = get_text()
st.set_page_config(page_title=f"Scraper - {T.get('page_title', 'Valuation')}", layout="wide")

# 2. SPRAWDZENIE AUTORYZACJI
check_auth()

# --- LOGIKA AUTOMATYCZNEGO ODŚWIEŻANIA ---
if "trigger_scrape" not in st.session_state:
    st.session_state["trigger_scrape"] = False

if "last_check_time" not in st.session_state:
    st.session_state["last_check_time"] = time.time()

@st.dialog("🔄 automation_dialog_title") # Klucz w i18n
def ask_for_scrape():
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
    st.session_state["timer_ping"] = time.time()

automation_timer()

current_time = time.time()
if st.session_state.get("auto_refresh_enabled", False):
    if current_time - st.session_state["last_check_time"] > 300:
        st.session_state["last_check_time"] = current_time
        ask_for_scrape()

# 4. INTERFEJS UŻYTKOWNIKA
st.title(f"🕵️ {T.get('scraper_title', 'Pobieranie danych')}")

city_config = {
    "Warszawa": ["bemowo", "bialoleka", "bielany", "mokotow", "ochota", "praga-poludnie", "praga-polnoc", "rembertow", "srodmiescie", "targowek", "ursus", "ursynow", "wawer", "wesola", "wilanow", "wlochy", "wola", "zoliborz"],
    "Krakow": ["stare-miasto", "grzegorzki", "pradnik-czerwony", "pradnik-bialy", "krowodrza", "bronowice", "zwierzyniec", "debniki", "lagiewniki-borek-falecki", "swoszowice", "podgorze-duchackie", "biezanow-prokocim", "podgorze", "czyzyny", "mistrzejowice", "bienczyce", "nowa-huta", "wzgorza-krzeslawickie"],
    "Wroclaw": ["stare-miasto", "srodmiescie", "krzyki", "fabryczna", "psie-pole"],
    "Gdansk": ["aniolki", "brzezno", "chelm", "jasien", "jelitkowo", "kokoszki", "letnica", "matarnia", "mlyniska", "nowy-port", "oliwa", "olszynka", "orunia", "osowa", "piecki-migowo", "przerobka", "przymorze", "rudniki", "siedlce", "stogi", "strzyza", "suchanino", "srodmiescie", "wrzeszcz", "zaspa", "zabianka"],
    "Poznan": ["grunwald", "jezyce", "nowe-miasto", "stare-miasto", "wilda"],
    "Lodz": ["baluty", "gorna", "polesie", "srodmiescie", "widzew"]
}

col1, col2 = st.columns(2)

with col1:
    city = st.selectbox(T.get("city_label", "Miasto"), list(city_config.keys()), key="selected_city_internal")
    
with col2:
    all_districts = city_config[city]
    districts = st.multiselect(
        T.get("dist_label", "Dzielnice"), 
        options=all_districts, 
        default=all_districts[:3],
        key="selected_districts_internal"
    )

pages = st.slider(T.get("pages_label", "Liczba stron"), 1, 20, 3)

# 5. LOGIKA SCRAPOWANIA
manual_trigger = st.button(T.get("run_scraper_btn", "🚀 Uruchom"), use_container_width=True)

if manual_trigger or st.session_state["trigger_scrape"]:
    st.session_state["trigger_scrape"] = False
    
    if not districts:
        st.error(T.get("error_no_districts", "Wybierz dzielnicę!"))
    else:
        db = get_db()
        scraper = OtodomScraper()
        
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
                final_df['owner'] = st.session_state['username']
                db.insert_offers(final_df, st.session_state['username'])
                st.success(T.get("scrape_success", "Zapisano!").format(count=len(final_df)))
                st.balloons()
                
                with st.expander(T.get("preview_header", "Podgląd")):
                    st.dataframe(final_df)
            else:
                st.error(T.get("error_empty_data", "Błąd: Brak danych po czyszczeniu."))
        else:
            st.error(T.get("error_no_results", "Nie pobrano danych."))

# 6. SIDEBAR - ZARZĄDZANIE
st.sidebar.divider()
st.sidebar.subheader(T.get("settings_header", "⚙️ Ustawienia"))

st.session_state["auto_refresh_enabled"] = st.sidebar.toggle(
    T.get("toggle_auto_refresh", "Autoodświeżanie"), 
    value=True
)

with st.sidebar.expander(T.get("db_mgmt_header", "⚠️ Zarządzanie bazą")):
    st.warning(T.get("delete_warning", "Usuniesz tylko SWOJE dane."))
    confirm_delete = st.checkbox(T.get("confirm_label", "Potwierdzam"))
    
    if st.button(T.get("delete_btn", "🗑️ Wyczyść dane"), disabled=not confirm_delete, type="primary"):
        try:
            delete_user_offers(st.session_state['username'])
            st.success(T.get("deleted_msg", "Wyczyszczono!"))
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")