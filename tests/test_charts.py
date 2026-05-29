import unittest
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def create_district_comparison_chart_LOCAL(df, city_name):
    """Kopia funkcji 1:1 z dashboardu do testów izolowanych"""
    if df is None or df.empty:
        return None

    df_clean = df.reset_index(drop=False)
    formatted_city = city_name.strip().capitalize()
    
    # 1. Szukamy kolumny lokalizacyjnej
    district_col = None
    for col in ['Dzielnica', 'district', 'subdistrict']:
        if col in df_clean.columns:
            district_col = col
            break

    # 2. Filtrowanie na wybrane miasto
    city_df = df_clean[
        (df_clean['city'].str.strip().str.lower() == city_name.strip().lower()) & 
        df_clean['price_per_m2'].notna()
    ]
    
    if city_df.empty:
        return None

    # --- SCENARIUSZ A: DZIELNICE ---
    if district_col:
        stats = city_df.groupby(district_col)['price_per_m2'].mean().reset_index()
        stats = stats.rename(columns={district_col: 'Dzielnica'})
        stats = stats.sort_values(by='price_per_m2', ascending=True)
        stats = stats[
            (stats['Dzielnica'].astype(str).str.strip() != "") & 
            (stats['Dzielnica'].astype(str).str.lower() != "none")
        ]
        
        if not stats.empty:
            fig = px.bar(
                stats, x='price_per_m2', y='Dzielnica', orientation='h',
                title=f"🏙️ Średnia cena za m² według dzielnic: {formatted_city}"
            )
            return fig

    # --- SCENARIUSZ B (FALLBACK): POKOJE ---
    if 'rooms' in city_df.columns:
        city_df['rooms_str'] = city_df['rooms'].fillna('Nieokreślone').astype(str) + " pok."
        stats = city_df.groupby('rooms_str')['price_per_m2'].mean().reset_index()
        
        fig = px.bar(
            stats, x='rooms_str', y='price_per_m2',
            title=f"🏠 Średnia cena za m² według liczby pokoi: {formatted_city} (Brak danych o dzielnicach)"
        )
        return fig

    return None

class TestDistrictComparisonChartFallback(unittest.TestCase):

    def setUp(self):
        """Przygotowanie danych testowych (brak kolumny Dzielnica)"""
        self.mock_data = {
            'city': ['Warszawa', 'Warszawa', 'Warszawa'],
            'price': [500000.0, 600000.0, 700000.0],
            'area': [50.0, 60.0, 70.0],
            'rooms': [2, 3, 3],
            'price_per_m2': [10000.0, 10000.0, 10000.0]
        }

    def test_fallback_to_rooms_when_district_column_is_missing(self):
        """Sprawdzenie przełączenia na kolumnę 'rooms'"""
        df_without_district = pd.DataFrame(self.mock_data)
        
        # Weryfikacja założeń testu
        self.assertNotIn('Dzielnica', df_without_district.columns)
        self.assertNotIn('district', df_without_district.columns)
        
        # Wywołanie lokalnej funkcji
        fig = create_district_comparison_chart_LOCAL(df_without_district, "Warszawa")
            
        # Sprawdzenie wyników
        self.assertIsNotNone(fig, "BŁĄD: Funkcja zwróciła None zamiast wykresu awaryjnego z pokojami!")
        self.assertIsInstance(fig, go.Figure)
        self.assertIn("liczby pokoi", fig.layout.title.text)

    def test_returns_none_when_dataframe_is_empty(self):
        empty_df = pd.DataFrame()
        fig = create_district_comparison_chart_LOCAL(empty_df, "Warszawa")
        self.assertIsNone(fig)

if __name__ == '__main__':
    unittest.main()