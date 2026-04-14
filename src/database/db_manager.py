from sqlalchemy import create_engine, text
import pandas as pd

class DBManager:
    """
    Klasa odpowiedzialna za zarządzanie bazą danych PostgreSQL.
    
    Obsługuje inicjalizację schematu bazy danych, masowe wstawianie ofert 
    nieruchomości oraz pobieranie danych do analizy w Streamlit.
    """

    def __init__(self):
        """Inicjalizuje połączenie z bazą danych real_estate."""
        self.url = "postgresql+psycopg2://admin:password@127.0.0.1:5432/real_estate"
        self.engine = create_engine(self.url)
    
    def create_tables(self):
        """
        Tworzy tabelę 'offers' w bazie danych, jeśli jeszcze nie istnieje.
        Definiuje kolumny takie jak cena, metraż, dzielnica i data pobrania.
        """

        query = """
        CREATE TABLE IF NOT EXISTS offers (
            id SERIAL PRIMARY KEY,
            title TEXT,
            city TEXT,
            district TEXT,
            subdistrict TEXT,
            price FLOAT,
            area FLOAT,
            rooms INTEGER,
            price_per_m2 FLOAT,
            source TEXT,
            scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.engine.begin() as conn:  # begin() automatycznie commit
            conn.execute(text(query))
    
    def insert_offers(self, df):
        """
        Zapisuje DataFrame z ofertami do tabeli 'offers'.
        
        Args:
            df (pd.DataFrame): Ramka danych zawierająca przetworzone oferty.
        """
        print("INSERTING:", len(df))
        print(df.dtypes)

        if df.empty:
            print("EMPTY DF - SKIP")
            return

        df.to_sql('offers', self.engine, if_exists='append', index=False)

    def get_all_offers(self):
        """
        Pobiera wszystkie rekordy z tabeli 'offers', sortując je od najnowszych.

        Returns:
            pd.DataFrame: Zbiór wszystkich ofert lub pusty DataFrame w przypadku błędu.
        """

        query = "SELECT * FROM offers ORDER BY scrape_date DESC"
        try:
            return pd.read_sql(query, self.engine)
        except Exception:
            return pd.DataFrame()