import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import os
from src.lang import get_text

class PricePredictor:
    def __init__(self):
        self.model = None
        self.model_path = "models/price_model.pkl"

    def train(self, df):
        """Trenuje model na podstawie danych z bazy."""
        from src.lang import get_text
        T = get_text()
        
        if df is None or df.empty:
            return False, T.get("no_data", "Brak danych.")

        # 1. DEFINIUJEMY KOLUMNY
        feature_cols = ['area', 'rooms', 'city', 'district']
        target_col = 'price'
        all_needed = feature_cols + [target_col]

        # 2. CZYSZCZENIE KOMPLEKSOWE
        # Usuwamy wiersze, które mają NaN w JAKIEJKOLWIEK z tych kolumn
        df_clean = df.dropna(subset=all_needed)
        
        # Opcjonalnie: upewniamy się, że typy numeryczne są poprawne
        df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors='coerce')
        df_clean = df_clean.dropna(subset=[target_col])

        if len(df_clean) < 10:
            return False, T.get("ml_too_little_data", "Zbyt mało danych (min. 10).")

        # 3. PRZYGOTOWANIE DANYCH
        X = df_clean[feature_cols]
        y = df_clean[target_col]

        # Reszta kodu Pipeline 
        categorical_features = ['city', 'district']
        categorical_transformer = OneHotEncoder(handle_unknown='ignore')

        preprocessor = ColumnTransformer(
            transformers=[('cat', categorical_transformer, categorical_features)],
            remainder='passthrough'
        )

        self.model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
        ])

        try:
            self.model.fit(X, y)
            
            if not os.path.exists('models'):
                os.makedirs('models')
            joblib.dump(self.model, self.model_path)
            return True, T.get("ml_train_success", "Model wytrenowany!")
        except Exception as e:
            return False, f"Błąd fit: {e}"

    def predict(self, area, rooms, city, district):
        """Przewiduje cenę dla podanych parametrów przez ML."""
        try:
            if self.model is None:
                if os.path.exists(self.model_path):
                    self.model = joblib.load(self.model_path)
                else:
                    return None
            
            input_data = pd.DataFrame([{
                'area': area,
                'rooms': rooms,
                'city': city,
                'district': district
            }])
            
            prediction = self.model.predict(input_data)[0]
            return round(prediction, 2)
        except Exception as e:
            print(f"Błąd predykcji ML: {e}")
            return None

def get_statistical_estimate(df, area, city, district, rooms):
    """
    Oblicza wartość nieruchomości na podstawie średniej ceny za m2,
    uwzględniając miasto, dzielnicę oraz liczbę pokoi.
    """
    # 1. Próba rygorystycznego dopasowania: Miasto + Dzielnica + Dokładna liczba pokoi
    subset = df[
        (df['city'] == city) & 
        (df['district'] == district) & 
        (df['rooms'] == rooms)
    ].copy()
    
    # Fallback 1: Jeśli w bazie jest za mało ofert (np. mniej niż 3) dla tych pokoi w dzielnicy,
    # ignorujemy pokoje i bierzemy ogólną średnią dla całej dzielnicy
    if subset.empty or len(subset) < 3:
        subset = df[(df['city'] == city) & (df['district'] == district)].copy()
        
    # Fallback 2: Jeśli cała dzielnica jest pusta, bierzemy średnią z całego miasta
    if subset.empty or len(subset) < 3:
        subset = df[df['city'] == city].copy()
        
    if subset.empty:
        return 0.0
        
    # 2. Obliczenie średniej ceny za metr i finalna wycena nieruchomości
    avg_price_m2 = subset['price_per_m2'].mean()
    
    return avg_price_m2 * area