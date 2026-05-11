import streamlit as st
import pandas as pd
from src.utils import get_db, clean_df
from src.analysis.charts import show_price_prediction_logic
from src.auth import check_auth

# 1. KONFIGURACJA
st.set_page_config(page_title="Analiza i Wycena", layout="wide")

# 2. ZABEZPIECZENIE
check_auth()

def main():
    st.title("📈 Analiza Statystyczna i Wycena")
    
    # Inicjalizacja bazy
    db = get_db()
    
    # Pobieramy username z sesji
    user_name_val = st.session_state.get('username')

    if not user_name_val:
        st.error("Błąd sesji: Nie znaleziono użytkownika.")
        st.stop()

    # Pobieranie ofert
    df_raw = db.get_all_offers(user_name_val) 
    df = clean_df(df_raw)

    if df is None or df.empty:
        st.warning(f"⚠️ Użytkownik {user_name_val} nie posiada danych.")
        return

    st.divider()
    st.subheader("💡 Kalkulator szacunkowej ceny")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            in_city = st.selectbox("Miasto", options=sorted(df["city"].unique()))
            in_area = st.number_input("Metraż (m²)", min_value=10, value=50)
        with col2:
            # Upewniamy się, że bierzemy dzielnice tylko dla wybranego miasta
            dist_list = sorted(df[df["city"] == in_city]["district"].unique())
            in_dist = st.selectbox("Dzielnica", options=dist_list)

        if st.button("🚀 Oblicz estymację ceny", use_container_width=True):
            # Pokazujemy logikę wyceny
            show_price_prediction_logic(df, in_area, in_city, in_dist)
                
            # 1. Nabijamy statystyki podstawowe
            db.update_stat(user_name_val, "valuation_requests_count")
            db.update_stat(user_name_val, "charts_generated_count")
            
            # --- LOGIKA: SPECJALISTA OD METRAŻU ---
            if 'searched_areas' not in st.session_state:
                st.session_state.searched_areas = set()
            
            # Dodajemy obecny metraż do zbioru w sesji
            st.session_state.searched_areas.add(in_area)
            
            # Jeśli użytkownik sprawdził 3 różne metraże, aktualizujemy "progres" 
            # Możemy użyć kolumny charts_generated_count jako wyznacznika wnikliwości 
            # lub po prostu sprawdzić to bezpośrednio w db_manager.
            # Dla uproszczenia: wysyłamy informację o "wnikliwości" do bazy
            if len(st.session_state.searched_areas) >= 3:
                # Tutaj możemy np. podbić licznik wykresów o dodatkowy punkt 
                # lub wywołać specjalną flagę. 
                # Załóżmy, że s_charts >= 15 to warunek na ten medal.
                db.update_stat(user_name_val, "charts_generated_count", value=5) # Bonus za wnikliwość
        
            # 2. SPRAWDZAMY OSIĄGNIĘCIA
            new_medals = db.check_and_update_achievements(user_name_val)
            for medal in new_medals:
                st.toast(f"🏆 Zdobyłeś nowe osiągnięcie: {medal}!")

    # Sekcja statystyk pod kalkulatorem (opcjonalnie)
    with st.expander("📊 Zobacz statystyki dla tej lokalizacji"):
        stats_df = df[(df["city"] == in_city) & (df["district"] == in_dist)]
        if not stats_df.empty:
            st.write(f"Średnia cena w tej dzielnicy: **{round(stats_df['price_per_m2'].mean(), 2)} zł/m²**")
        else:
            st.write("Brak szczegółowych danych dla tej dzielnicy.")

if __name__ == "__main__":
    main()