import streamlit as st
import pandas as pd
from src.utils import get_db, clean_df
from src.scraper.otodom import OtodomScraper
from src.auth import check_auth

check_auth()

st.set_page_config(page_title="Scraper - Pobieranie Danych", layout="wide")
st.title("🕵️ Pobieranie danych z Otodom")

# --- KOMPLETNA KONFIGURACJA TOP 6 ---
# Klucze muszą odpowiadać nazwom w URL Otodom (małe litery, bez polskich znaków)
city_config = {
    "Warszawa": [
        "bemowo", "bialoleka", "bielany", "mokotow", "ochota", "praga-poludnie", 
        "praga-polnoc", "rembertow", "srodmiescie", "targowek", "ursus", 
        "ursynow", "wawer", "wesola", "wilanow", "wlochy", "wola", "zoliborz"
    ],
    "Krakow": [
        "stare-miasto", "grzegorzki", "pradnik-czerwony", "pradnik-bialy", 
        "krowodrza", "bronowice", "zwierzyniec", "debniki", "lagiewniki-borek-falecki", 
        "swoszowice", "podgorze-duchackie", "biezanow-prokocim", "podgorze", 
        "czyzyny", "mistrzejowice", "bienczyce", "nowa-huta", "wzgorza-krzeslawickie"
    ],
    "Wroclaw": [
        "stare-miasto", "srodmiescie", "krzyki", "fabryczna", "psie-pole"
    ],
    "Gdansk": [
        "aniolki", "brzezno", "chelm", "jasien", "jelitkowo", "kokoszki", 
        "letnica", "matarnia", "mlyniska", "nowy-port", "oliwa", "olszynka", 
        "orunia", "osowa", "piecki-migowo", "przerobka", "przymorze", "rudniki", 
        "siedlce", "stogi", "strzyza", "suchanino", "srodmiescie", "u參與", 
        "wrzeszcz", "zaspa", "zabianka"
    ],
    "Poznan": [
        "grunwald", "jezyce", "nowe-miasto", "stare-miasto", "wildaj"
    ],
    "Lodz": [
        "baluty", "gorna", "polesie", "srodmiescie", "widzew"
    ]
}

# --- INTERFEJS UŻYTKOWNIKA ---
col1, col2 = st.columns(2)

with col1:
    city = st.selectbox("Wybierz miasto z TOP 6:", list(city_config.keys()))
    
with col2:
    # Wybieramy domyślnie wszystkie dzielnice dla danego miasta
    all_districts = city_config[city]
    districts = st.multiselect(
        "Wybierz dzielnice:", 
        options=all_districts, 
        default=all_districts[:3] # Domyślnie zaznacz pierwsze trzy, żeby nie przeciążać serwera
    )

pages = st.slider("Liczba stron do przeszukania (na każdą dzielnicę):", 1, 20, 3)

st.info("ℹ️ Scraper odwiedzi każdą wybraną dzielnicę osobno, co zwiększa dokładność danych.")

if st.button("🚀 Uruchom pobieranie", use_container_width=True):
    if not districts:
        st.error("Wybierz przynajmniej jedną dzielnicę!")
    else:
        db = get_db()
        scraper = OtodomScraper()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_data = []
        
        # Pobieranie danych dzielnica po dzielnicy
        for i, dist in enumerate(districts):
            status_text.text(f"Pobieranie: {city} - {dist}...")
            try:
                # Wywołujemy scraper dla konkretnej dzielnicy
                df_dist = scraper.fetch_data(city, max_pages=pages, selected_districts=[dist])
                if df_dist is not None and not df_dist.empty:
                    total_data.append(df_dist)
            except Exception as e:
                st.warning(f"Błąd przy pobieraniu {dist}: {e}")
            
            # Aktualizacja paska postępu
            progress_bar.progress((i + 1) / len(districts))

        # Łączenie i zapisywanie danych
        if total_data:
            final_df = pd.concat(total_data, ignore_index=True)
            final_df = clean_df(final_df)
            
            if not final_df.empty:
                # Zapis do bazy
                final_df['owner'] = st.session_state['username']
                db.insert_offers(final_df)
                st.success(f"✅ Sukces! Pobrano i zapisano {len(final_df)} ofert dla miasta {city}.")
                st.balloons()
                
                with st.expander("Podgląd pobranych danych"):
                    st.dataframe(final_df.head(20))
            else:
                st.error("Dane zostały pobrane, ale proces czyszczenia (clean_df) zwrócił pustą tabelę.")
        else:
            st.error("Nie udało się pobrać żadnych ofert. Sprawdź połączenie lub spróbuj ponownie później.")

st.sidebar.divider()
st.sidebar.subheader("Zarządzanie bazą")

# Wykorzystujemy 'expander' lub 'popover', żeby przycisk nie był na wierzchu
with st.sidebar.expander("⚠️ Opcje zaawansowane"):
    st.warning("Usuniesz tylko SWOJE dane.")
    confirm_delete = st.checkbox("Potwierdzam chęć usunięcia moich danych")
    
    if st.button("🗑️ Wyczyść moje oferty", disabled=not confirm_delete, type="primary"):
        # Używamy funkcji z auth.py, którą przygotowaliśmy wcześniej
        from src.auth import delete_user_offers
        
        try:
            delete_user_offers(st.session_state['username'])
            st.success("Twoje dane zostały usunięte!")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")