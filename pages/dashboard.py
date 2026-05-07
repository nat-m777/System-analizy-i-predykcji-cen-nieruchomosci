import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import get_db, clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
# Importujemy funkcje autoryzacji
from src.auth import init_auth_db, login_user, register_user, save_search, get_search_history
from src.auth import check_auth

check_auth()

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dashboard - Analiza Rynku", layout="wide")

def main():
    # Inicjalizacja tabel auth w Postgresie
    init_auth_db()

    # --- DASHBOARD DLA ZALOGOWANYCH ---
    st.sidebar.success(f"Zalogowany: **{st.session_state['username']}**")
    if st.sidebar.button("Wyloguj"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("📊 Przegląd Rynku i Analiza Anomalii")

    if 'username' not in st.session_state:
        st.error("Błąd sesji: Nie znaleziono nazwy użytkownika.")
        st.stop()
    
    username = st.session_state['username']

    # 1. POBIERANIE I CZYSZCZENIE DANYCH
    db = get_db()
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df.empty:
        st.info("Baza danych jest pusta. Pobierz dane za pomocą Scrapera.")
        return

    # Normalizacja nazw kolumn
    if "district" in df.columns:
        df = df.rename(columns={"district": "Dzielnica"})
    df["Dzielnica"] = df["Dzielnica"].astype(str)

    # --- SIDEBAR: FILTRY ---
    st.sidebar.header("🔍 Filtry")
    
    all_cities = sorted(df["city"].unique())
    selected_cities = st.sidebar.multiselect("Wybierz miasta", all_cities, default=all_cities)

    df_temp = df[df["city"].isin(selected_cities)]
    all_districts = sorted(df_temp["Dzielnica"].unique())
    
    selected_districts = st.sidebar.multiselect("Wybierz dzielnice", all_districts, default=all_districts)

    # PRZYCISK ZAPISU HISTORII
    if st.sidebar.button("💾 Zapisz to wyszukiwanie"):
        save_search(st.session_state['username'], selected_cities, selected_districts)
        st.sidebar.toast("Zapisano w Twojej historii!")

    df_filtered = df_temp[df_temp["Dzielnica"].isin(selected_districts)].copy()

    if df_filtered.empty:
        st.warning("Brak danych dla wybranych filtrów.")
        return
    
    st.sidebar.divider()
    st.sidebar.subheader("🗑️ Zarządzanie Twoimi danymi")

    # Używamy st.expander, żeby nie kliknąć przez przypadek
    with st.sidebar.expander("Opcje usuwania"):
        st.warning("Ta akcja usunie wszystkie Twoje ogłoszenia z bazy.")
        conf = st.text_input("Wpisz 'USUŃ', aby potwierdzić")
        
        if st.button("Potwierdź usuwanie danych", type="primary"):
            if conf == "USUŃ":
                from src.auth import delete_user_offers
                delete_user_offers(st.session_state['username'])
                st.success("Twoje dane zostały usunięte.")
                st.rerun()
            else:
                st.error("Błędne hasło potwierdzające.")

    # --- LOGIKA WYKRYWANIA ANOMALII ---
    def mark_outliers(group):
        if len(group) < 5:
            group['status'] = "✅ W normie"
            return group
        Q1, Q3 = group['price_per_m2'].quantile(0.25), group['price_per_m2'].quantile(0.75)
        IQR = Q3 - Q1
        group['status'] = "✅ W normie"
        group.loc[group['price_per_m2'] < (Q1 - 1.5 * IQR), 'status'] = "🔥 Okazja"
        group.loc[group['price_per_m2'] > (Q3 + 1.5 * IQR), 'status'] = "💎 Premium"
        return group

    df_filtered = df_filtered.groupby('Dzielnica', group_keys=False).apply(mark_outliers)
    df_filtered = df_filtered.reset_index(drop=True)
    df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated()]

    # --- METRYKI I ZAKŁADKI ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liczba ofert", len(df_filtered))
    m2.metric("Śr. cena/m²", f"{round(df_filtered['price_per_m2'].mean(), 0)} zł")
    m3.metric("Okazje", len(df_filtered[df_filtered['status'] == "🔥 Okazja"]))
    m4.metric("Premium", len(df_filtered[df_filtered['status'] == "💎 Premium"]))

    # Dodajemy piątą zakładkę: Historia
    t1, t2, t3, t4, t5 = st.tabs(["📊 Rozkład", "📈 Cena/Metraż", "🚩 Anomalie", "🏙️ Miasta", "📜 Moja Historia"])

    with t1:
        st.plotly_chart(create_price_histogram(df_filtered), use_container_width=True)
    with t2:
        st.plotly_chart(create_area_vs_price_chart(df_filtered), use_container_width=True)

    with t3:
        st.subheader("🕵️ Anomalie (filtrowane per miasto)")
        
        # 1. ZAPEWNIENIE, ŻE DZIELNICA JEST KOLUMNĄ
        df_for_anomalies = df_filtered.copy()
        if "Dzielnica" not in df_for_anomalies.columns:
            df_for_anomalies = df_for_anomalies.reset_index()

        # 2. BEZPIECZNE USUWANIE DUPLIKATÓW
        # Sprawdzamy co mamy w kolumnach, żeby nie wywalić KeyError
        cols_to_check = ['title', 'price', 'area', 'Dzielnica']
        existing_subset = [c for c in cols_to_check if c in df_for_anomalies.columns]
        df_unique = df_for_anomalies.drop_duplicates(subset=existing_subset)
        
        for city in selected_cities:
            city_df = df_unique[df_unique["city"] == city].copy()
            if len(city_df) > 5:
                Q1 = city_df['price_per_m2'].quantile(0.25)
                Q3 = city_df['price_per_m2'].quantile(0.75)
                IQR = Q3 - Q1
                
                # Definiujemy granice
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = city_df[
                    ((city_df['price_per_m2'] < lower_bound) | (city_df['price_per_m2'] > upper_bound)) &
                    (city_df['status'] != "✅ W normie")
                ].copy()
                
                if not outliers.empty:
                    st.write(f"### Miasto: {city}")
                    outliers['Data'] = outliers['scrape_date'].dt.strftime('%Y-%m-%d')
                    
                    # Wyświetlamy tylko to co na pewno jest w outliers
                    display_cols = ["status", "title", "Dzielnica", "price_per_m2", "Data"]
                    existing_display = [c for c in display_cols if c in outliers.columns]
                    
                    st.dataframe(
                        outliers[existing_display].sort_values("price_per_m2"), 
                        use_container_width=True, 
                        hide_index=True
                    )
    with t4:
        # Statystyki miast (TOP 6)
        top6 = ["Warszawa", "Krakow", "Wroclaw", "Gdansk", "Poznan", "Lodz"]
        city_choice = st.selectbox("Wybierz miasto do analizy:", [c for c in top6 if c in df["city"].unique()])
        if city_choice:
            stats = df[df["city"] == city_choice].groupby("Dzielnica")["price_per_m2"].mean().reset_index()
            fig = px.bar(stats, x="Dzielnica", y="price_per_m2", title=f"Średnie ceny w {city_choice}")
            st.plotly_chart(fig, use_container_width=True)

    with t5:
        st.subheader("📜 Twoje ostatnie wyszukiwania")
        history = get_search_history(st.session_state['username'])
        if not history.empty:
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("Nie masz jeszcze zapisanych wyszukiwań.")

    # --- LISTA OFERT (NA DOLE) ---
    st.divider()
    st.subheader("📋 Ostatnio pobrane ogłoszenia")
    view_df = df_filtered.sort_values("scrape_date", ascending=False).head(100).copy()
    view_df["Cena"] = view_df["price"].apply(lambda x: f"{x:,.0f} zł".replace(",", " "))
    
    desired_cols = ["status", "title", "Dzielnica", "Cena", "area", "scrape_date"]
    st.dataframe(view_df[[c for c in desired_cols if c in view_df.columns]], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()