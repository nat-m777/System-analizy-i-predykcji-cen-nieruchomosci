import streamlit as st
import pandas as pd
import time
from src.utils import get_db, clean_df
from src.scraper.otodom import OtodomScraper
from src.auth import check_auth, delete_user_offers
from src.i18n import LANGUAGES
T = LANGUAGES[st.session_state.get('lang', 'PL')]

# 1. KONFIGURACJA STRONY (Musi być pierwsza!)
st.set_page_config(page_title="Scraper - Pobieranie Danych", layout="wide")

# 2. SPRAWDZENIE AUTORYZACJI
check_auth()

# --- LOGIKA AUTOMATYCZNEGO ODŚWIEŻANIA ---
if "trigger_scrape" not in st.session_state:
    st.session_state["trigger_scrape"] = False

if "last_check_time" not in st.session_state:
    st.session_state["last_check_time"] = time.time()

@st.dialog("🔄 Automatyczne odświeżanie")
def ask_for_scrape():
    st.write("Minęło 5 minut. Czy chcesz ponownie pobrać dane?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Tak, pobierz", type="primary"):
            st.session_state["trigger_scrape"] = True
            st.rerun()
    with col2:
        if st.button("Nie teraz"):
            st.rerun()

@st.fragment(run_every="5m")
def automation_timer():
    # Ten fragment tylko "puka" do aplikacji co 5 minut
    # Nie robimy tu nic, sam fakt wywołania fragmentu co 5min 
    # odświeży stan poniższego warunku w głównym skrypcie
    st.session_state["timer_ping"] = time.time()

# Uruchomienie cichego licznika
automation_timer()

# Sprawdzamy warunek wyświetlenia okna w głównym nurcie kodu, 
# ale TYLKO jeśli upłynęło min. 5 minut od ostatniej akcji
current_time = time.time()
if st.session_state.get("auto_refresh_enabled", False):
    if current_time - st.session_state["last_check_time"] > 300: # 300 sekund = 5 min
        st.session_state["last_check_time"] = current_time
        ask_for_scrape()

# 4. INTERFEJS UŻYTKOWNIKA
st.title("🕵️ Pobieranie danych z Otodom")

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
    city = st.selectbox("Wybierz miasto:", list(city_config.keys()), key="selected_city_internal")
    
with col2:
    all_districts = city_config[city]
    districts = st.multiselect(
        "Wybierz dzielnice:", 
        options=all_districts, 
        default=all_districts[:3],
        key="selected_districts_internal"
    )

pages = st.slider("Liczba stron na dzielnicę:", 1, 20, 3)

# 5. LOGIKA SCRAPOWANIA
manual_trigger = st.button("🚀 Uruchom pobieranie", use_container_width=True)

if manual_trigger or st.session_state["trigger_scrape"]:
    st.session_state["trigger_scrape"] = False # Reset flagi
    
    if not districts:
        st.error("Wybierz przynajmniej jedną dzielnicę!")
    else:
        db = get_db()
        scraper = OtodomScraper()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_data = []
        
        for i, dist in enumerate(districts):
            status_text.text(f"Pobieranie: {city} - {dist}...")
            try:
                df_dist = scraper.fetch_data(city, max_pages=pages, selected_districts=[dist])
                if df_dist is not None and not df_dist.empty:
                    total_data.append(df_dist)
            except Exception as e:
                st.warning(f"Błąd przy {dist}: {e}")
            progress_bar.progress((i + 1) / len(districts))

        if total_data:
            final_df = pd.concat(total_data, ignore_index=True)
            final_df = clean_df(final_df)
            
            if not final_df.empty:
                # PRZYPISANIE WŁAŚCICIELA
                final_df['owner'] = st.session_state['username']
                
                db.insert_offers(final_df, st.session_state['username'])
                st.success(f"✅ Zapisano {len(final_df)} ofert dla użytkownika {st.session_state['username']}.")
                st.balloons()
                
                with st.expander("Podgląd danych"):
                    st.dataframe(final_df.head(len(final_df)))
            else:
                st.error("Błąd: Dane po oczyszczeniu są puste.")
        else:
            st.error("Nie pobrano żadnych danych.")

# 6. SIDEBAR - ZARZĄDZANIE
st.sidebar.divider()
st.sidebar.subheader("⚙️ Ustawienia")

st.session_state["auto_refresh_enabled"] = st.sidebar.toggle(
    "Autoodświeżanie (5 min)", 
    value=True
)

with st.sidebar.expander("⚠️ Zarządzanie bazą"):
    st.warning("Usuniesz tylko SWOJE dane.")
    confirm_delete = st.checkbox("Potwierdzam")
    
    if st.button("🗑️ Wyczyść moje oferty", disabled=not confirm_delete, type="primary"):
        try:
            delete_user_offers(st.session_state['username'])
            st.success("Wyczyszczono!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")