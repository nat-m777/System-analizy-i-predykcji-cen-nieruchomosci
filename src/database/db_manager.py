import os
from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st

class DBManager:
    def __init__(self):
        self.url = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:password@127.0.0.1:5432/real_estate")
        self.engine = create_engine(self.url)
        # Automatycznie dbamy o strukturę przy starcie
        self.create_tables()
        self.fix_schema()

    def create_tables(self):
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

    def fix_schema(self):
        """Dodaje brakujące kolumny, jeśli baza została utworzona wcześniej."""
        with self.engine.begin() as conn:
            # Dodajemy username jeśli go nie ma (jako alias dla owner lub dodatkowe info)
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS username TEXT;"))
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS owner TEXT;"))

    def insert_offers(self, df, username):
        if df is None or df.empty:
            print("EMPTY DF - SKIP INSERT")
            return

        # Czyścimy dane i przypisujemy użytkownika
        df = df.copy() # Pracujemy na kopii, by nie psuć oryginału w Streamlit
        df['owner'] = username
        df['username'] = username # Na wszelki wypadek wypełniamy obie kolumny

        # =====================================
        # CLEAN TYPES
        # =====================================
        numeric_cols = ["price", "area", "rooms", "price_per_m2"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "scrape_date" in df.columns:
            df["scrape_date"] = pd.to_datetime(df["scrape_date"], errors="coerce")

        # Filtrujemy tylko te kolumny, które faktycznie chcemy w bazie
        # (Zapobiega to błędom, gdy w DF są jakieś tymczasowe kolumny ze scrapera)
        valid_columns = [
            "title", "city", "district", "subdistrict", "price", "area", 
            "rooms", "price_per_m2", "url", "source", "scrape_date", "owner", "username"
        ]
        
        # Zostawiamy tylko te kolumny, które istnieją w DF i są na liście valid_columns
        cols_to_save = [c for c in valid_columns if c in df.columns]
        df_to_save = df[cols_to_save].where(pd.notnull(df), None)

        try:
            df_to_save.to_sql(
                "offers",
                self.engine,
                if_exists="append",
                index=False,
                method="multi"
            )
            print(f"✅ INSERT SUCCESS: {len(df_to_save)} offers for {username}")
        except Exception as e:
            print(f"❌ INSERT ERROR: {e}")
            raise e

    def get_all_offers(self, username=None):
        """Pobiera oferty. Jeśli podano username, filtruje tylko dla tego użytkownika."""
        if username:
            query = text("SELECT * FROM offers WHERE owner = :u OR username = :u ORDER BY scrape_date DESC")
            return pd.read_sql(query, self.engine, params={"u": username})
        
        query = "SELECT * FROM offers ORDER BY scrape_date DESC"
        return pd.read_sql(query, self.engine)

    def clear_all_data(self):
        query = text("TRUNCATE TABLE offers RESTART IDENTITY")
        with self.engine.begin() as conn:
            conn.execute(query)
        return True