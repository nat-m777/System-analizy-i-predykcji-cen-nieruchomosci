import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df
from src.auth import check_auth

# 1. KONFIGURACJA
st.set_page_config(page_title="Porównanie Miast", layout="wide")

# 2. ZABEZPIECZENIE
check_auth()

def main():
    st.title("🏙️ Analiza Porównawcza Miast")
    st.markdown("Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki.")

    if 'username' not in st.session_state:
        st.error("Błąd sesji: Nie znaleziono nazwy użytkownika.")
        st.stop()
    
    username = st.session_state['username']
    db = get_db()
    
    # 3. POBIERANIE I CZYSZCZENIE DANYCH
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {username} nie posiada danych w bazie.")
        return

    # --- PANEL BOCZNY (WYBÓR) ---
    st.sidebar.header("Konfiguracja Porównania")
    real_cities_in_db = sorted(df["city"].unique())

    selected_cities = st.sidebar.multiselect(
        "Wybierz miasta do porównania (max 3):",
        options=real_cities_in_db,
        default=real_cities_in_db[:3] if len(real_cities_in_db) >= 3 else real_cities_in_db
    )   
    
    if not selected_cities:
        st.info("Wybierz miasta w panelu bocznym po lewej.")
        return

    # --- BLOKADA > 3 (ZGODNIE Z TWOJĄ PROŚBĄ) ---
    if len(selected_cities) > 3:
        st.error("Proszę wybrać maksymalnie 3 miasta, aby zachować czytelność wykresów.")
        return

    # --- LOGIKA OSIĄGNIĘCIA: PORÓWNYWACZ MIAST ---
    # Używamy st.session_state do śledzenia UNIKALNYCH miast wybranych w tej sesji
    if "cities_compared_total" not in st.session_state:
        st.session_state.cities_compared_total = set()

    # Dodajemy aktualnie wybrane miasta do zbioru unikalnych miast
    st.session_state.cities_compared_total.update(selected_cities)
    
    # Aktualizujemy bazę danych o łączną liczbę unikalnych miast, które użytkownik już "porównał"
    total_compared = len(st.session_state.cities_compared_total)
    db.update_stat(username, "cities_viewed_count", value=total_compared, increment=False)

    # Sprawdzamy czy wpadło osiągnięcie (min. 5 miast w sumie)
    if total_compared >= 5:
        try:
            from database.db_manager import check_all_achievements
            check_all_achievements(db, username)
        except ImportError:
            pass

    # --- FILTROWANIE I WYKRESY ---
    df_comp = df[df["city"].isin(selected_cities)].copy()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Średnia cena za m²")
        avg_price = df_comp.groupby("city")["price_per_m2"].mean().sort_values().reset_index()
        fig1 = px.bar(avg_price, x="city", y="price_per_m2", color="city", text_auto='.0f')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("2. Rozkład metrażu (Boxplot)")
        fig2 = px.box(df_comp, x="city", y="area", color="city", points=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("3. Relacja ceny do metrażu")
    fig3 = px.scatter(df_comp, x="area", y="price", color="city", hover_data=["city", "district"])
    st.plotly_chart(fig3, use_container_width=True)

    # Tabela
    st.subheader("📊 Zestawienie liczbowe")
    summary = df_comp.groupby("city").agg({"price_per_m2": ["mean", "median"], "price": "count"}).reset_index()
    summary.columns = ["Miasto", "Średnia PLN/m²", "Mediana PLN/m²", "Liczba ofert"]
    st.dataframe(summary, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()