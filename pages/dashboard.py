import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from src.utils import get_db, clean_df
from src.analysis.charts import create_price_histogram, create_area_vs_price_chart
from src.auth import init_auth_db, save_search, get_search_history, check_auth, delete_user_offers

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dashboard - Analiza Nieruchomości", layout="wide")

def init_session_state():
    """Inicjalizacja zmiennych w pamięci podręcznej."""
    if 'stats' not in st.session_state:
        st.session_state.stats = {
            "cities_viewed": set(),
            "charts_generated": 0,
            "valuation_requests": 0
        }

def render_sidebar(df, db, username):
    """Renderuje pasek boczny z filtrami i trofeami."""
    st.sidebar.success(f"Zalogowany: **{username}**")
    
    if st.sidebar.button("Wyloguj"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.sidebar.header("🔍 Filtry")
    
    all_cities = sorted(df["city"].unique())
    selected_cities = st.sidebar.multiselect("Wybierz miasta", all_cities, default=all_cities)
    
    # Aktualizacja statystyki miast w bazie
    if selected_cities:
        st.session_state.stats["cities_viewed"].update(selected_cities)
        db.update_stat(username, "cities_viewed_count", value=len(st.session_state.stats["cities_viewed"]), increment=False)

    df_temp = df[df["city"].isin(selected_cities)]
    all_districts = sorted(df_temp["Dzielnica"].unique())
    selected_districts = st.sidebar.multiselect("Wybierz dzielnice", all_districts, default=all_districts)

    if st.sidebar.button("💾 Zapisz wyszukiwanie"):
        save_search(username, selected_cities, selected_districts)
        st.sidebar.toast("Zapisano!")

    # Sekcja Osiągnięć w Sidebarze
    st.sidebar.divider()
    st.sidebar.subheader("🏅 Twoje Trofea")
    unlocked = db.get_user_achievements(username)
    
    badges = {
        "Badacz rynku": "🔍", "Eksplorator danych": "📈", 
        "Porównywacz miast": "⚖️", "Specjalista od metrażu": "📏", "Ekspert wyceny": "💰"
    }
    
    cols = st.sidebar.columns(5)
    for i, (name, icon) in enumerate(badges.items()):
        is_unlocked = name in unlocked
        opacity = "1.0" if is_unlocked else "0.2"
        grayscale = "0%" if is_unlocked else "100%"
        cols[i].markdown(f"<div title='{name}' style='font-size:25px; filter:grayscale({grayscale}); opacity:{opacity};'>{icon}</div>", unsafe_allow_html=True)

    return selected_cities, selected_districts

def mark_outliers(group):
    if len(group) < 5: return group.assign(status="✅ W normie")
    q1, q3 = group['price_per_m2'].quantile([0.25, 0.75])
    iqr = q3 - q1
    group['status'] = "✅ W normie"
    group.loc[group['price_per_m2'] < (q1 - 1.5 * iqr), 'status'] = "🔥 Okazja"
    group.loc[group['price_per_m2'] > (q3 + 1.5 * iqr), 'status'] = "💎 Premium"
    return group

def main():
    check_auth()
    init_auth_db()
    init_session_state()
    
    db = get_db()
    username = st.session_state.get('username')

    # 1. Pobieranie danych
    df_raw = db.get_all_offers(username)
    df = clean_df(df_raw)

    if df.empty:
        st.title("📊 Przegląd Rynku")
        st.info("Brak danych. Uruchom scraper, aby zasilić bazę.")
        return

    # Normalizacja
    if "district" in df.columns:
        df = df.rename(columns={"district": "Dzielnica"})
    df["Dzielnica"] = df["Dzielnica"].astype(str)

    # 2. Sidebar i Filtry
    selected_cities, selected_districts = render_sidebar(df, db, username)

    # 3. Logika filtrowania
    df_filtered = df[df["city"].isin(selected_cities) & df["Dzielnica"].isin(selected_districts)].copy()

    df_filtered['status'] = "✅ W normie"

    if not df_filtered.empty:
        df_filtered = df_filtered.groupby('Dzielnica', group_keys=False).apply(mark_outliers)

    # 4. Dashboard UI
    st.title("📊 Przegląd Rynku")
    
    # Metryki
    okazje_count = len(df_filtered[df_filtered['status'] == "🔥 Okazja"]) if 'status' in df_filtered.columns else 0
    premium_count = len(df_filtered[df_filtered['status'] == "💎 Premium"]) if 'status' in df_filtered.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liczba ofert", len(df_filtered))
    m2.metric("Śr. cena/m²", f"{round(df_filtered['price_per_m2'].mean(), 0)} zł" if not df_filtered.empty else "0 zł")
    m3.metric("Okazje", okazje_count)
    m4.metric("Premium", premium_count)

    t1, t2, t3, t4, t5 = st.tabs(["📊 Rozkład", "📈 Cena/Metraż", "🚩 Anomalie", "🏙️ Miasta", "📜 Historia"])

    with t1:
        st.plotly_chart(create_price_histogram(df_filtered), use_container_width=True)
    
    with t2:
        st.plotly_chart(create_area_vs_price_chart(df_filtered), use_container_width=True)

    with t4:
        top6 = ["Warszawa", "Krakow", "Wroclaw", "Gdansk", "Poznan", "Lodz"]
        city_choice = st.selectbox("Szczegóły miasta:", [c for c in top6 if c in df["city"].unique()])
        if city_choice:
            # NABICIE STATYSTYKI WYKRESÓW
            db.update_stat(username, "charts_generated_count")
            # Wewnątrz main() po aktualizacji statystyk:
            new_medals = db.check_and_update_achievements(username)

            for medal in new_medals:
                st.toast(f"🏆 Zdobyłeś nowe osiągnięcie: {medal}!")
            stats_city = df[df["city"] == city_choice].groupby("Dzielnica")["price_per_m2"].mean().reset_index()
            st.plotly_chart(px.bar(stats_city, x="Dzielnica", y="price_per_m2", color="price_per_m2"), use_container_width=True)

    # 5. Końcowe sprawdzanie osiągnięć za pomocą nowej metody z DBManager
    new_medals = db.check_and_update_achievements(username)
    for medal in new_medals:
        st.toast(f"🏆 Zdobyłeś nowe osiągnięcie: {medal}!")

    # Tabela na dole
    st.divider()
    st.dataframe(df_filtered.sort_values("scrape_date", ascending=False).head(50), use_container_width=True)

if __name__ == "__main__":
    main()