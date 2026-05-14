import streamlit as st
import json
import os

def get_text():
    # Pobieramy język z sesji (domyślnie PL)
    lang = st.session_state.get("lang", "PL").lower()
    
    # Budujemy ścieżkę do pliku json: src/i18n/pl.json
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "i18n", f"{lang}.json")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Awaryjny komunikat, jeśli plik zniknie
        return {"error": f"Missing translation file: {lang}.json"}