import sys
import os

# Dodanie głównego katalogu projektu do ścieżki wyszukiwania Pythona
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.database.db_manager import DBManager

def test_insert_and_calculation():
    print("🚀 Inicjalizacja DBManager...")
    db = DBManager()
    
    # 1. Tworzymy sztuczne dane testowe BEZ kolumny 'price_per_m2'
    print("\n📦 Przygotowanie testowych danych ze scrapera (brak kolumny price_per_m2)...")
    test_data = {
        "title": ["Testowe mieszkanie Mokotów 1", "Testowe Mieszkanie Mokotów 2"],
        "city": ["Warszawa", "Warszawa"],
        "district": ["mokotow", "mokotow"],
        "price": [1000000.0, 600000.0], # 1 mln i 600 tys
        "area": [50.0, 30.0],           # 50m2 i 30m2
        "rooms": [2, 1],
        "url": ["https://test1.pl", "https://test2.pl"],
        "source": ["test_scraper", "test_scraper"]
    }
    df_test = pd.DataFrame(test_data)
    
    # 2. Próba zapisu do bazy danych
    print("\n💾 Uruchamianie metody insert_offers()...")
    try:
        db.insert_offers(df_test, username="test_user")
        print("➡️ Metoda wykonała się bez błędów krytycznych.")
    except Exception as e:
        print(f"❌ Coś poszło nie tak podczas zapisu: {e}")
        return

    # 3. Pobranie danych z powrotem i sprawdzenie efektu
    print("\n🔍 Pobieranie zapisanych danych z bazy w celu weryfikacji...")
    df_recovered = db.get_all_offers()
    
    # Filtrujemy tylko nasze testowe rekordy
    df_recovered = df_recovered[df_recovered['source'] == 'test_scraper']
    
    if df_recovered.empty:
        print("❌ Błąd: Nie znaleziono testowych rekordów w bazie danych!")
        return
        
    print("\n📊 WYNIK WERYFIKACJI KOLUMN:")
    print(df_recovered[["title", "price", "area", "price_per_m2"]])
    
    # Ostateczny sprawdzian matematyczny
    for idx, row in df_recovered.iterrows():
        expected_price_m2 = row['price'] / row['area']
        if row['price_per_m2'] == expected_price_m2:
            print(f"✅ Sukces dla '{row['title']}': Cena za m2 wynosi {row['price_per_m2']} (Wyliczona poprawnie!)")
        else:
            print(f"❌ Błąd dla '{row['title']}': Oczekiwano {expected_price_m2}, a w bazie jest {row['price_per_m2']}")

if __name__ == "__main__":
    test_insert_and_calculation()