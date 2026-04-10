from sqlalchemy import create_engine, text
import pandas as pd

class DBManager:
    def __init__(self):
        self.url = "postgresql+psycopg2://admin:password@127.0.0.1:5432/real_estate"
        self.engine = create_engine(self.url)
    
    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS offers (
            id SERIAL PRIMARY KEY,
            title TEXT,
            city TEXT,
            district TEXT,
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
        if df.empty:
            return
        df.to_sql('offers', self.engine, if_exists='append', index=False)

    def get_all_offers(self):
        query = "SELECT * FROM offers ORDER BY scrape_date DESC"
        try:
            return pd.read_sql(query, self.engine)
        except Exception:
            return pd.DataFrame()