import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df
from src.auth import check_auth

# 1. KONFIGURACJA (Musi być na samym początku, przed jakimkolwiek kodem st.)
st.set_page_config(page_title="Porównanie TOP 6", layout="wide")

# 2. ZABEZPIECZENIE
check_auth()

def main():
    st.title("🏙️ Analiza Porównawcza Miast")
    st.markdown("Wybierz maksymalnie **3 miasta**, aby zestawić ich statystyki.")

    # Sprawdzenie username w sesji
    if 'username' not in st.session_state:
        st.error("Błąd sesji: Nie znaleziono nazwy użytkownika.")
        st.stop()
    
    username = st.session_state['username']

    # 3. POBIERANIE I CZYSZCZENIE DANYCH (Z poprawionym argumentem)
    db = get_db()
    df_raw = db.get_all_offers(username) # POPRAWKA: dodano username
    df = clean_df(df_raw)
    
    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {username} nie posiada danych w bazie. Uruchom scraper, aby zasilić bazę.")
        return

    # --- PANEL BOCZNY (WYBÓR) ---
    st.sidebar.header("Konfiguracja Porównania")

    # Pobieramy to, co faktycznie jest w bazie użytkownika
    real_cities_in_db = sorted(df["city"].unique())

    selected_cities = st.sidebar.multiselect(
        "Wybierz miasta do porównania (max 3):",
        options=real_cities_in_db,
        default=real_cities_in_db[:3] if len(real_cities_in_db) >= 3 else real_cities_in_db
    )   
    
    if not selected_cities:
        st.info("Wybierz miasta w panelu bocznym po lewej.")
        return

    if len(selected_cities) > 3:
        st.error("Proszę wybrać maksymalnie 3 miasta, aby zachować czytelność wykresów.")
        return

    # Filtrowanie danych do wybranych miast
    df_comp = df[df["city"].isin(selected_cities)].copy()

    # --- WYKRESY ANALITYCZNE ---
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Średnia cena za m²")
        avg_price = df_comp.groupby("city")["price_per_m2"].mean().sort_values().reset_index()
        fig1 = px.bar(
            avg_price, x="city", y="price_per_m2", 
            color="city", text_auto='.0f',
            labels={"price_per_m2": "PLN/m²", "city": "Miasto"}
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("2. Rozkład metrażu (Boxplot)")
        fig2 = px.box(
            df_comp, x="city", y="area", color="city",
            labels={"area": "Powierzchnia (m²)", "city": "Miasto"},
            points=False 
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("3. Relacja całkowitej ceny do metrażu")
    fig3 = px.scatter(
        df_comp, x="area", y="price", color="city", 
        hover_data=["district"], opacity=0.6,
        labels={"area": "Metraż (m²)", "price": "Cena całkowita (PLN)"}
    )
    st.plotly_chart(fig3, use_container_width=True)

    # --- TABELA PODSUMOWUJĄCA ---
    st.subheader("📊 Zestawienie liczbowe")
    summary = df_comp.groupby("city").agg({
        "price_per_m2": ["mean", "median"],
        "price": "count"
    }).reset_index()
    summary.columns = ["Miasto", "Średnia PLN/m²", "Mediana PLN/m²", "Liczba ofert"]
    st.table(summary.style.format({
        "Średnia PLN/m²": "{:.0f}",
        "Mediana PLN/m²": "{:.0f}"
    }))

if __name__ == "__main__":
    main()