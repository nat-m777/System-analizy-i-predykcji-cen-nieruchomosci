import os
from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st

class DBManager:
    """
    Manager bazy danych obsługujący połączenie z PostgreSQL.
    Zarządza schematem tabel, operacjami CRUD na ofertach nieruchomości
    oraz systemem statystyk i osiągnięć użytkowników.
    """
    def __init__(self):
        # Bezpieczne sprawdzenie sekretów bez wywoływania błędu
        self.db_url = None
        
        try:
            # Próba pobrania ze Streamlit Secrets
            if "DATABASE_URL" in st.secrets:
                self.db_url = st.secrets["DATABASE_URL"]
        except Exception:
            # Jeśli st.secrets wyrzuci błąd (np. brak pliku), szukamy w systemie
            self.db_url = os.getenv("DATABASE_URL")

        # Jeśli nadal nie ma URL (np. uruchamiasz lokalnie bez Dockera)
        if not self.db_url:
            self.db_url = "postgresql+psycopg2://[LOGIN]:[HASŁO]@127.0.0.1:5432/real_estate"
        self.engine = create_engine(self.db_url)
        # Automatyczne przygotowanie struktury bazy przy starcie aplikacji
        self.create_tables()
        self.fix_schema()

    def create_tables(self):
        """Tworzy strukturę tabel, jeśli jeszcze nie istnieją w bazie danych."""
        with self.engine.begin() as conn:
            # 1. Tabela USERS - Przechowuje poświadczenia użytkowników
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                );
            """))

            # 2. Tabela OFFERS - Główny magazyn ofert nieruchomości zebranych przez scraper
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS offers (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    city TEXT,
                    district TEXT,
                    price DOUBLE PRECISION,
                    area DOUBLE PRECISION,
                    rooms INTEGER,
                    price_per_m2 DOUBLE PRECISION,
                    source TEXT,
                    scrape_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    url TEXT,
                    subdistrict TEXT,
                    owner TEXT DEFAULT 'admin',
                    username TEXT
                );
            """))

            # 3. Tabela SEARCH_HISTORY - Rejestruje filtry wyszukiwania używane przez użytkowników
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    city TEXT,
                    districts TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))

            # 4. Tabela ACHIEVEMENTS - Przechowuje odblokowane "medale" użytkowników
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id SERIAL PRIMARY KEY,
                    username TEXT REFERENCES users(username) ON DELETE CASCADE,
                    achievement_name TEXT NOT NULL,
                    achieved_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(username, achievement_name)
                );
            """))

            # 5. Tabela USER_STATS - Liczniki aktywności służące do wyliczania osiągnięć
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                    cities_viewed_count INTEGER DEFAULT 0,
                    charts_generated_count INTEGER DEFAULT 0,
                    valuation_requests_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

    def fix_schema(self):
        """Metoda migracyjna - dodaje brakujące kolumny w przypadku aktualizacji bazy."""
        with self.engine.begin() as conn:
            # Dodanie kolumny url, która spowodowała błąd:
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS url TEXT;"))
            
            # Zabezpieczenie na wypadek innych brakujących kolumn:
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS subdistrict TEXT;"))
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS price_per_m2 DOUBLE PRECISION;"))
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS source TEXT;"))
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS username TEXT;"))
            conn.execute(text("ALTER TABLE offers ADD COLUMN IF NOT EXISTS owner TEXT;"))

            # 2. AUTOMATYCZNA NAPRAWA: Uzupełnianie pustych cen za m2 dla starych danych
            conn.execute(text("""
                UPDATE offers 
                SET price_per_m2 = price / area 
                WHERE price_per_m2 IS NULL AND area > 0;
            """))

    def insert_offers(self, df, username):
        """
        Czyści dane w DataFrame i masowo zapisuje je do tabeli offers.
        
        Args:
            df (pd.DataFrame): Surowe dane ze scrapera.
            username (str): Login użytkownika dodającego dane.
        """
        if df is None or df.empty:
            print("EMPTY DF - SKIP INSERT")
            return

        # Przypisanie własności do importowanych rekordów
        df = df.copy() 
        df['owner'] = username
        df['username'] = username

        # Konwersja typów danych (coerce zamienia błędy na NaN/None)
        numeric_cols = ["price", "area", "rooms", "price_per_m2"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "price_per_m2" not in df.columns or df["price_per_m2"].isnull().all():
            # Upewniamy się, że cena i metraż są liczbami
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["area"] = pd.to_numeric(df["area"], errors="coerce")
            
            # Bezpieczne dzielenie (jeśli area > 0)
            df["price_per_m2"] = df.apply(
                lambda row: row["price"] / row["area"] if pd.notna(row["price"]) and pd.notna(row["area"]) and row["area"] > 0 else None,
                axis=1
            )

        if "scrape_date" in df.columns:
            df["scrape_date"] = pd.to_datetime(df["scrape_date"], errors="coerce")

        # Mapowanie kolumn z DataFrame na schemat tabeli SQL
        valid_columns = [
            "title", "city", "district", "subdistrict", "price", "area", 
            "rooms", "price_per_m2", "url", "source", "scrape_date", "owner", "username"
        ]
        
        cols_to_save = [c for c in valid_columns if c in df.columns]
        df_to_save = df[cols_to_save].where(pd.notnull(df), None)

        try:
            # Wykorzystanie pandas to_sql z metodą 'multi' dla zwiększenia wydajności zapisu
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
        """Pobiera oferty z bazy. Filtruje wyniki, jeśli podano konkretnego użytkownika."""
        if username:
            query = text("SELECT * FROM offers WHERE owner = :u OR username = :u ORDER BY scrape_date DESC")
            return pd.read_sql(query, self.engine, params={"u": username})
        
        query = "SELECT * FROM offers ORDER BY scrape_date DESC"
        return pd.read_sql(query, self.engine)

    def clear_all_data(self):
        """Usuwa wszystkie oferty z tabeli offers i resetuje licznik ID."""
        query = text("TRUNCATE TABLE offers RESTART IDENTITY")
        with self.engine.begin() as conn:
            conn.execute(query)
        return True

    def unlock_achievement(self, username, achievement_name):
        """Przyznaje osiągnięcie użytkownikowi, ignorując powtórzenia (ON CONFLICT)."""
        query = text("""
            INSERT INTO achievements (username, achievement_name) 
            VALUES (:u, :name) 
            ON CONFLICT DO NOTHING
        """)
        with self.engine.begin() as conn:
            conn.execute(query, {"u": username, "name": achievement_name})

    def get_user_achievements(self, username):
        """Zwraca listę nazw wszystkich osiągnięć zdobytych przez użytkownika."""
        query = text("SELECT achievement_name FROM achievements WHERE username = :u")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"u": username}).fetchall()
            return [r[0] for r in result]

    def update_stat(self, username, column_name, value=1, increment=True):
        """
        Aktualizuje statystyki aktywności użytkownika. Obsługuje inkrementację (np. liczniki)
        oraz ustawianie sztywnych wartości (np. liczba unikalnych miast).
        """
        if increment:
            # UPSERT: Dodaje wartość do istniejącego licznika
            query = text(f"""
                INSERT INTO user_stats (username, {column_name}) 
                VALUES (:u, :v) 
                ON CONFLICT (username) 
                DO UPDATE SET {column_name} = user_stats.{column_name} + :v, last_updated = CURRENT_TIMESTAMP
            """)
        else:
            # UPSERT: Nadpisuje istniejącą wartość
            query = text(f"""
                INSERT INTO user_stats (username, {column_name}) 
                VALUES (:u, :v) 
                ON CONFLICT (username) 
                DO UPDATE SET {column_name} = :v, last_updated = CURRENT_TIMESTAMP
            """)
            
        with self.engine.begin() as conn:
            conn.execute(query, {"u": username, "v": value})

    def check_and_update_achievements(self, username):
        """
        Sprawdza progi statystyk i przyznaje nowe osiągnięcia.
        Zwraca listę nowo odblokowanych medali do wyświetlenia powiadomień w UI.
        """
        # 1. Pobranie bieżących liczników użytkownika
        query = text("SELECT cities_viewed_count, charts_generated_count, valuation_requests_count FROM user_stats WHERE username = :u")
        with self.engine.connect() as conn:
            res = conn.execute(query, {"u": username}).fetchone()
        
        if not res:
            return []

        s_cities, s_charts, s_valuations = res
        unlocked = self.get_user_achievements(username)
        newly_unlocked = []

        # Mapa warunków: (Nazwa osiągnięcia, Warunek logiczny)
        achievements_to_check = [
            ("Badacz rynku", s_cities >= 3),
            ("Eksplorator danych", s_charts >= 10),
            ("Porównywacz miast", s_cities >= 5),
            ("Specjalista od metrażu", s_charts >= 15),
            ("Ekspert wyceny", s_valuations >= 25)
        ]

        # Weryfikacja i zapis nowych osiągnięć
        for name, condition in achievements_to_check:
            if condition and name not in unlocked:
                self.unlock_achievement(username, name)
                newly_unlocked.append(name)
                
        return newly_unlocked