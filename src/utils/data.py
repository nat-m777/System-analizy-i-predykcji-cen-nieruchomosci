import pandas as pd

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Czyści, formatuje i waliduje dane pobrane z bazy danych.
    """
    # 1. Sprawdzenie czy dane w ogóle istnieją
    if df is None or df.empty:
        return pd.DataFrame()

    # Tworzymy kopię, aby nie modyfikować oryginalnego obiektu w pamięci
    df = df.copy()

    # 2. Inteligentna obsługa kolumny 'dzielnica'
    # Różne źródła danych mogą nazywać tę kolumnę inaczej (district/subdistrict)
    if "district" in df.columns:
        if "subdistrict" in df.columns:
            df = df.drop(columns=["subdistrict"])
    elif "subdistrict" in df.columns:
        df = df.rename(columns={"subdistrict": "district"})
    else:
        # Jeśli brakuje kolumny, tworzymy ją jako placeholder
        df["district"] = "Nieznana"

    # 3. Standaryzacja tekstów
    # Usuwamy białe znaki i dbamy o wielkość liter w miastach
    df["city"] = df["city"].astype(str).str.strip().str.capitalize()
    
    # Obsługa pustych wartości w dzielnicach
    df["district"] = df["district"].fillna("Nieznana").astype(str).replace(["None", "nan", ""], "Nieznana")

    # 4. Konwersja typów numerycznych
    # errors='coerce' zamieni błędne wpisy (np. tekst w cenie) na NaN
    num_cols = ["price", "area", "price_per_m2", "rooms"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Filtracja rekordów
    # Usuwamy oferty, które nie mają kluczowych informacji (ceny lub metrażu)
    df = df.dropna(subset=["price", "area"])
    
    # Usuwamy skrajne błędy (np. cena 0 zł)
    df = df[df["price"] > 0]

    return df


def get_city_stats(df: pd.DataFrame, city_name: str):
    """
    Pomocnicza funkcja do szybkiego wyciągania statystyk dla konkretnego miasta.
    """
    city_df = df[df["city"] == city_name]
    if city_df.empty:
        return None
    
    return {
        "avg_price": city_df["price"].mean(),
        "avg_m2": city_df["price_per_m2"].mean(),
        "count": len(city_df)
    }