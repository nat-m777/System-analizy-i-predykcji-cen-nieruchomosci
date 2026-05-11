import streamlit as st
import pandas as pd
from src.utils import get_db, clean_df
from src.analysis.charts import show_price_prediction_logic
from src.auth import check_auth

# 1. KONFIGURACJA (Musi być na samym początku)
st.set_page_config(page_title="Analiza i Wycena", layout="wide")

# 2. ZABEZPIECZENIE
check_auth()

def main():
    st.title("📈 Analiza Statystyczna i Wycena")
    
    # 1. POBIERANIE DANYCH I DB
    db = get_db()
    
    # Pobieramy username z sesji
    username = st.session_state.get('username')

    if not username:
        st.error("Błąd sesji: Nie znaleziono nazwy użytkownika. Zaloguj się ponownie.")
        st.stop()

    # Pobieranie ofert dla zalogowanego użytkownika
    df_raw = db.get_all_offers(username) 
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {username} nie posiada danych do analizy. Uruchom scraper!")
        return

    # --- SEKCJA: KALKULATOR WYCENY ---
    st.divider()
    st.subheader("💡 Kalkulator szacunkowej ceny mieszkania")
    st.info("Kalkulator oblicza cenę na podstawie średnich rynkowych z Twoich ofert.")

    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            in_city = st.selectbox(
                "Wybierz miasto", 
                options=sorted(df["city"].unique()),
                key="city_select"
            )
            in_area = st.number_input("Metraż (m²)", min_value=10, max_value=500, value=50)

        with col2:
            available_districts = sorted(df[df["city"] == in_city]["district"].unique())
            in_dist = st.selectbox(
                "Wybierz dzielnicę", 
                options=available_districts,
                key="dist_select"
            )
            in_rooms = st.slider("Liczba pokoi", 1, 10, 2)

        # PRZYCISK WYCENY
        if st.button("🚀 Oblicz estymację ceny", use_container_width=True):
            # Pokazujemy logikę wyceny
            show_price_prediction_logic(df, in_area, in_city, in_dist)
                
           # 1. Nabijamy statystykę wyceny (+1)
            db.update_stat(username, "valuation_requests_count")
            
            # 2. Nabijamy statystykę wygenerowanych wykresów (+1), 
            # bo funkcja show_price_prediction_logic generuje wykresy
            db.update_stat(username, "charts_generated_count")
        
            # 3. SPRAWDZAMY OSIĄGNIĘCIA (Nowa metoda z Managera)
            new_medals = db.check_and_update_achievements(username)
            #LOGIKA: SPECJALISTA OD METRAŻU
            if 'unique_areas_checked' not in st.session_state:
                st.session_state.unique_areas_checked = set()
            
            # Dodajemy aktualny metraż do zbioru (set automatycznie usuwa duplikaty)
            st.session_state.unique_areas_checked.add(in_area)
            
            # Jeśli sprawdzono 3 różne metraże, podbijamy statystykę w bazy,
            # która odpowiada za odblokowanie tego konkretnego medalu
            if len(st.session_state.unique_areas_checked) >= 3:
                # Zakładamy, że w db_manager ten medal wymaga np. charts_generated_count >= 15
                # Dodajemy bonusowe punkty do progresu
                db.update_stat(username, "charts_generated_count", value=5)
            for medal in new_medals:
                st.toast(f"🏆 Zdobyłeś nowe osiągnięcie: {medal}!")

    # --- SEKCJA: DODATKOWE STATYSTYKI ---
    st.divider()
    with st.expander("📊 Zobacz statystyki dla wybranej lokalizacji"):
        stats_df = df[df["city"] == in_city]
        if in_dist:
            stats_df = stats_df[stats_df["district"] == in_dist]
        
        if not stats_df.empty:
            avg_price = stats_df["price_per_m2"].mean()
            median_price = stats_df["price_per_m2"].median()
            min_price = stats_df["price_per_m2"].min()
            max_price = stats_df["price_per_m2"].max()
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1: st.metric("Średnia m²", f"{round(avg_price, 2)} zł")
            with col_m2: st.metric("Mediana m²", f"{round(median_price, 2)} zł")
            with col_m3: st.metric("Min m²", f"{round(min_price, 2)} zł")
            with col_m4: st.metric("Max m²", f"{round(max_price, 2)} zł")
            st.caption(f"Statystyki oparte na {len(stats_df)} ofertach.")
        else:
            st.write("Zbyt mało danych dla tej lokalizacji.")

if __name__ == "__main__":
    main()