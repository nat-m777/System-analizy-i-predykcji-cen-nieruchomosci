import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df
from src.auth import check_auth
from src.i18n import LANGUAGES
T = LANGUAGES[st.session_state.get('lang', 'PL')]

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Ranking Miast - Analiza Nieruchomości", layout="wide")

# --- ZABEZPIECZENIE (Musisz być zalogowany) ---
check_auth()

def main():
    st.title("🏆 Rankingowy System Nieruchomości")
    st.markdown("Porównaj średnie ceny mieszkań dla **TOP 6** miast w Polsce.")

    # Inicjalizacja bazy
    db = get_db()
    username = st.session_state.get('username')

    # Sprawdzenie sesji (na wszelki wypadek)
    if not username:
        st.error("Błąd sesji. Zaloguj się ponownie.")
        st.stop()

    # 1. POBIERANIE I CZYSZCZENIE DANYCH (Wszystkich ofert użytkownika)
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {username} nie posiada danych w bazie. Uruchom scraper!")
        return

    # --- KONFIGURACJA RANKINGU ---
    # 1. Definiujemy listę miast w różnych wariantach (z polskimi znakami i bez)
    # To rozwiąże problem, jeśli w bazie masz "Krakow" zamiast "Kraków"
    city_map = {
        "warszawa": "Warszawa",
        "kraków": "Kraków", "krakow": "Kraków",
        "wrocław": "Wrocław", "wroclaw": "Wrocław",
        "gdańsk": "Gdańsk", "gdansk": "Gdańsk",
        "poznań": "Poznań", "poznan": "Poznań",
        "łódź": "Łódź", "lodz": "Łódź"
    }

    # 2. Normalizujemy kolumnę 'city' w Twoim DataFrame
    df["city_lower"] = df["city"].str.lower().str.strip()

    # 3. Filtrujemy tylko te rekordy, które są w naszym słowniku
    df_ranking = df[df["city_lower"].isin(city_map.keys())].copy()

    # 4. Mapujemy nazwy na ładne, oficjalne brzmienie
    df_ranking["city"] = df_ranking["city_lower"].map(city_map)

    if df_ranking.empty:
        st.warning(f"⚠️ W bazie użytkownika {username} nie znaleziono ofert dla TOP 6 miast.")
        st.info("Sprawdź czy w Twoich danych kolumna 'city' zawiera nazwy takie jak: Kraków, Wrocław, Gdańsk itd.")
        return

    # --- PANEL BOCZNY - FILTRY RANKINGU ---
    st.sidebar.header("⚖️ Filtry Rankingu")

    # Filtrowanie po Metrażu (Slider z krokiem 5m)
    min_area = int(df_ranking["area"].min())
    max_area = int(df_ranking["area"].max())
    selected_area = st.sidebar.slider(
        "Wybierz zakres metrażu (m²):", 
        min_value=10, 
        max_value=250, # Stały zakres dla czytelności rankingu
        value=(min_area, max_area),
        step=5
    )

    # Filtrowanie po Liczbie Pokoi
    real_rooms = sorted(df_ranking["rooms"].unique())
    selected_rooms = st.sidebar.multiselect(
        "Liczba pokoi:", 
        options=real_rooms, 
        default=real_rooms
    )

    # Przyciski do szybkiego wyboru (Opcjonalnie)
    # st.sidebar.markdown("**Szybki wybór pokoi:**")
    # if st.sidebar.button("Wszystkie"): selected_rooms = real_rooms

    # --- APLIKACJA FILTRÓW ---
    df_filtered = df_ranking[
        (df_ranking["area"] >= selected_area[0]) & 
        (df_ranking["area"] <= selected_area[1]) &
        (df_ranking["rooms"].isin(selected_rooms))
    ]

    # --- UI: PREZENTACJA RANKINGU ---
    st.subheader(f"📊 Porównanie Średniej Ceny za m² w TOP 6")
    

    if not df_filtered.empty:
        # Obliczanie średniej dla miast
        ranking_data = df_filtered.groupby("city").agg({
            "price_per_m2": "mean",
            "price": "count" # Liczba ofert do hover_data
        }).reset_index()

        # Sortowanie od najwyższej ceny
        ranking_data = ranking_data.sort_values("price_per_m2", ascending=False)

        # GENEROWANIE WYKRESU PLOTLY
        fig = px.bar(
            ranking_data, 
            x="city", 
            y="price_per_m2",
            color="city", # Każde miasto ma swój kolor
            text_auto='.0f', # Wyświetlanie wartości nad słupkiem (zaokrąglone)
            labels={"price_per_m2": "Średnia PLN/m²", "city": "Miasto"},
            hover_data=["price"] # Dodatkowa informacja o liczbie ofert w tooltipie
        )

        # Stylowanie wykresu
        fig.update_layout(
            yaxis_title="Średnia cena za m² (PLN)",
            xaxis_title="Miasto",
            showlegend=False, # Legenda niepotrzebna, kolory są na osi X
            font=dict(size=14)
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()

        # --- TABELA RANKINGOWA ---
        st.subheader("📑 Tabela Rankingowa")
        # Zmiana nazw kolumn do wyświetlenia
        ranking_display = ranking_data.rename(columns={
            "city": "Miasto",
            "price_per_m2": "Średnia PLN/m²",
            "price": "Liczba Ofert"
        })
        
        # Wyświetlenie interaktywnej tabeli
        st.dataframe(ranking_display.style.format({
            "Średnia PLN/m²": "{:.0f}"
        }), use_container_width=True, hide_index=True)

    else:
        st.info("Nie znaleziono ofert spełniających wybrane kryteria w 6 największych miastach.")

if __name__ == "__main__":
    main()