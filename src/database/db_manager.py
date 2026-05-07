import os
from sqlalchemy import create_engine, text
import pandas as pd

class DBManager:
    """
    Klasa odpowiedzialna za zarządzanie bazą danych PostgreSQL.
    
    Obsługuje inicjalizację schematu bazy danych, masowe wstawianie ofert 
    nieruchomości oraz pobieranie danych do analizy w Streamlit.
    """

    def __init__(self):
        # Pobiera URL z systemu (Docker) lub używa lokalnego jeśli uruchamiasz ręcznie
        self.url = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:password@127.0.0.1:5432/real_estate")
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
            url TEXT UNIQUE,
            source TEXT,
            scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            owner TEXT
        );
        """
        with self.engine.begin() as conn:
            conn.execute(text(query))
    
    def insert_offers(self, df):

        if df is None or df.empty:
            print("EMPTY DF - SKIP INSERT")
            return

        print(f"INSERTING: {len(df)} offers")

        # =====================================
        # CLEAN TYPES
        # =====================================

        numeric_cols = [
            "price",
            "area",
            "rooms",
            "price_per_m2"
        ]

        for col in numeric_cols:

            if col in df.columns:

                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

        # datetime
        if "scrape_date" in df.columns:

            df["scrape_date"] = pd.to_datetime(
                df["scrape_date"],
                errors="coerce"
            )

        # text columns
        text_cols = [
            "title",
            "city",
            "district",
            "subdistrict",
            "url",
            "source"
        ]

        for col in text_cols:

            if col in df.columns:

                df[col] = df[col].astype(str)

        # NaN -> None
        df = df.where(pd.notnull(df), None)

        # =====================================
        # INSERT
        # =====================================

        try:
            df['owner'] = st.session_state['username']
            df.to_sql(
                "offers",
                self.engine,
                if_exists="append",
                index=False,
                method="multi"
            )

            print("✅ INSERT SUCCESS")

        except Exception as e:

            print("❌ INSERT ERROR")
            print(e)

            print("\n=== DF INFO ===")
            print(df.dtypes)

            print("\n=== SAMPLE ===")
            print(df.head())

            raise e

    def get_all_offers(self):
        """
        Pobiera wszystkie rekordy z tabeli 'offers', sortując je od najnowszych.

        Returns:
            pd.DataFrame: Zbiór wszystkich ofert lub pusty DataFrame w przypadku błędu.
        """
        query = "SELECT * FROM offers ORDER BY scrape_date DESC"
        try:
            return pd.read_sql(query, self.engine)
        except Exception as e:
            print(f"Błąd podczas pobierania danych: {e}")
            return pd.DataFrame()
    
    def clear_all_data(self):
        """
        Całkowicie czyści tabelę z ofertami w bazie PostgreSQL.
        Używa instrukcji TRUNCATE, która jest szybsza i resetuje liczniki ID.
        """
        query = text("TRUNCATE TABLE offers RESTART IDENTITY")
        try:
            with self.engine.begin() as conn:
                conn.execute(query)
            print("Baza danych PostgreSQL została wyczyszczona (TRUNCATE).")
            return True
        except Exception as e:
            print(f"Błąd podczas czyszczenia bazy: {e}")
            return False