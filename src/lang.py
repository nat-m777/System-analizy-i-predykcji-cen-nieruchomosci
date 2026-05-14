import streamlit as st
import json
import os

def get_text():
    """
    Ładuje słownik tłumaczeń na podstawie języka wybranego w sesji użytkownika.
    
    Funkcja szuka plików JSON w folderze 'src/i18n/'. 
    Przykład: jeśli st.session_state['lang'] == "PL", wczytany zostanie plik 'pl.json'.
    
    Returns:
        dict: Słownik zawierający klucze i wartości tłumaczeń dla interfejsu.
    """
    # 1. Pobranie preferencji językowych z session_state.
    # Domyślnie ustawiamy "PL", jeśli użytkownik jeszcze nic nie wybrał.
    lang = st.session_state.get("lang", "PL").lower()
    
    # 2. Dynamiczne budowanie ścieżki do pliku tłumaczeń.
    # Wykorzystujemy os.path.abspath, aby skrypt działał poprawnie niezależnie 
    # od tego, z jakiego folderu uruchomiono aplikację Streamlit.
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "i18n", f"{lang}.json")
    
    try:
        # 3. Otwarcie i sparsowanie pliku JSON z kodowaniem UTF-8 (obsługa polskich znaków).
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    except FileNotFoundError:
        # 4. Fallback: Jeśli plik języka nie istnieje, zwracamy komunikat o błędzie.
        # Warto w tym miejscu dodać logikę domyślnego ładowania pliku 'pl.json' jako backup.
        return {"error": f"Missing translation file: {lang}.json"}