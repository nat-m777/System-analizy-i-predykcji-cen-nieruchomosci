import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import os

class PricePredictor:
    def __init__(self):
        self.model = None
        self.model_path = "models/price_model.pkl"

    def train(self, df):
        """Trenuje model na podstawie danych z bazy."""
        if df.empty or len(df) < 10:
            return False, "Zbyt mało danych do trenowania (min. 10 ofert)."

        # Przygotowanie cech
        X = df[['area', 'rooms', 'city', 'district']]
        y = df['price']

        categorical_features = ['city', 'district']
        categorical_transformer = OneHotEncoder(handle_unknown='ignore')

        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', categorical_transformer, categorical_features)
            ],
            remainder='passthrough'
        )

        self.model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
        ])

        self.model.fit(X, y)
        
        if not os.path.exists('models'):
            os.makedirs('models')
        joblib.dump(self.model, self.model_path)
        
        return True, "Model został wytrenowany pomyślnie."

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

def get_statistical_estimate(df, area, city, district):
    """Oblicza wycenę na podstawie średniej ceny za m2 (Statystyka)."""
    try:
        # 1. Próba wyceny na podstawie dzielnicy
        subset = df[(df['city'] == city) & (df['district'] == district)]
        
        # 2. Fallback do całego miasta, jeśli w dzielnicy nie ma ofert
        if subset.empty:
            subset = df[df['city'] == city]
            
        if not subset.empty:
            avg_m2 = subset['price_per_m2'].mean()
            return round(avg_m2 * area, 2)
        
        return None
    except Exception as e:
        print(f"Błąd wyceny statystycznej: {e}")
        return None