import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df
from src.auth import check_auth
from src.lang import get_text # Używamy ustandaryzowanej funkcji pobierającej teksty

# --- KONFIGURACJA STRONY ---
T = get_text()
st.set_page_config(page_title=f"{T['page_title']} - Ranking", layout="wide")

# --- ZABEZPIECZENIE ---
check_auth()

def main():
    st.title(f"🏆 {T.get('tab_cities', 'Ranking Miast')}")
    st.markdown(T.get('comp_desc', "Porównaj średnie ceny mieszkań dla **TOP 6** miast w Polsce."))

    # Inicjalizacja bazy
    db = get_db()
    username = st.session_state.get('username')

    if not username:
        st.error(T.get('error_db', "Błąd sesji. Zaloguj się ponownie."))
        st.stop()

    # 1. POBIERANIE I CZYSZCZENIE DANYCH
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(T["no_data"])
        return

    # --- KONFIGURACJA RANKINGU ---
    city_map = {
        "warszawa": "Warszawa",
        "kraków": "Kraków", "krakow": "Kraków",
        "wrocław": "Wrocław", "wroclaw": "Wrocław",
        "gdańsk": "Gdańsk", "gdansk": "Gdańsk",
        "poznań": "Poznań", "poznan": "Poznań",
        "łódź": "Łódź", "lodz": "Łódź"
    }

    df["city_lower"] = df["city"].str.lower().str.strip()
    df_ranking = df[df["city_lower"].isin(city_map.keys())].copy()
    df_ranking["city"] = df_ranking["city_lower"].map(city_map)

    if df_ranking.empty:
        st.warning(T["no_data"])
        return

    # --- PANEL BOCZNY - FILTRY ---
    st.sidebar.header(f"⚖️ {T['dash_filters']}")

    min_area = int(df_ranking["area"].min())
    max_area = int(df_ranking["area"].max())
    
    selected_area = st.sidebar.slider(
        f"{T['area_label']}:", 
        min_value=10, 
        max_value=250, 
        value=(min_area, max_area),
        step=5
    )

    real_rooms = sorted(df_ranking["rooms"].unique())
    selected_rooms = st.sidebar.multiselect(
        f"{T['rooms_label']}:", 
        options=real_rooms, 
        default=real_rooms
    )

    # --- APLIKACJA FILTRÓW ---
    df_filtered = df_ranking[
        (df_ranking["area"] >= selected_area[0]) & 
        (df_ranking["area"] <= selected_area[1]) &
        (df_ranking["rooms"].isin(selected_rooms))
    ]

    # --- UI: PREZENTACJA RANKINGU ---
    st.subheader(f"📊 {T.get('comp_chart_avg', 'Porównanie Średniej Ceny za m²')}")

    if not df_filtered.empty:
        # Obliczanie średniej
        ranking_data = df_filtered.groupby("city").agg({
            "price_per_m2": "mean",
            "price": "count" 
        }).reset_index()

        ranking_data = ranking_data.sort_values("price_per_m2", ascending=False)

        # GENEROWANIE WYKRESU
        fig = px.bar(
            ranking_data, 
            x="city", 
            y="price_per_m2",
            color="city",
            text_auto='.0f',
            labels={
                "price_per_m2": T.get('dash_avg_m2', "Średnia PLN/m²"), 
                "city": T.get('dash_select_city', "Miasto")
            },
            hover_data=["price"]
        )

        fig.update_layout(
            yaxis_title=T.get('dash_avg_m2', "Średnia cena za m² (PLN)"),
            xaxis_title=T.get('dash_select_city', "Miasto"),
            showlegend=False,
            font=dict(size=14)
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()

        # --- TABELA RANKINGOWA ---
        st.subheader(f"📑 {T.get('comp_table_header', 'Tabela Rankingowa')}")
        
        ranking_display = ranking_data.rename(columns={
            "city": T.get('dash_select_city', "Miasto"),
            "price_per_m2": T.get('dash_avg_m2', "Średnia PLN/m²"),
            "price": T.get('metric_offers', "Liczba Ofert")
        })
        
        st.dataframe(ranking_display.style.format({
            T.get('dash_avg_m2', "Średnia PLN/m²"): "{:.0f}"
        }), use_container_width=True, hide_index=True)

    else:
        st.info(T["no_data"])

if __name__ == "__main__":
    main()