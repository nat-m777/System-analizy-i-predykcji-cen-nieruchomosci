import pandas as pd
import unicodedata
from datetime import datetime
from fpdf import FPDF

def safe_text(text):
    """
    Czyści tekst z polskich znaków, aby standardowe czcionki FPDF nie wyrzucały błędów.
    """
    if not text or pd.isna(text): 
        return "N/A"
    
    # Normalizacja Unicode i zamiana specyficznych znaków
    text = str(text)
    normalized = "".join(
        c for c in unicodedata.normalize('NFKD', text) 
        if not unicodedata.combining(c)
    )
    return normalized.replace('ł', 'l').replace('Ł', 'L')

def generate_valuation_pdf(params, price_est, translation_map):
    """
    Uniwersalna funkcja generująca PDF.
    params: słownik z danymi (klucz: etykieta, wartość: dane)
    price_est: wyliczona cena
    translation_map: aktualny słownik T z wybranej strony
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # 1. Nagłówek raportu
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(41, 128, 185) 
        pdf.cell(0, 20, safe_text(translation_map.get("pdf_title", "RAPORT")), ln=True, align='C')
        
        # 2. Data wygenerowania
        pdf.set_font("Arial", size=10)
        pdf.set_text_color(0, 0, 0)
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
        pdf.cell(0, 10, f"{safe_text(translation_map.get('pdf_date', 'Data'))}: {date_str}", ln=True, align='C')
        pdf.ln(10)
        
        # 3. Parametry nieruchomości
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, safe_text(translation_map.get("pdf_params", "Parametry:")), ln=True)
        
        pdf.set_font("Arial", size=12)
        for label, value in params.items():
            pdf.cell(0, 10, f"- {safe_text(label)}: {safe_text(value)}", ln=True)
        
        pdf.ln(10)
        
        # 4. Sekcja z ceną końcową
        pdf.set_fill_color(235, 245, 251)
        pdf.set_font("Arial", 'B', 16)
        
        val_label = translation_map.get('pdf_value', 'VALUE')
        formatted_price = f"{int(price_est):,}".replace(',', ' ')
        val_str = f"{val_label}: {formatted_price} PLN"
        
        pdf.cell(0, 20, safe_text(val_str), border=1, ln=True, align='C', fill=True)
        
        # 5. Przygotowanie wyjścia dla Streamlit
        output = pdf.output()
        if isinstance(output, bytearray):
            return bytes(output)
        elif isinstance(output, str):
            return output.encode('latin-1')
        return output
        
    except Exception as e:
        print(f"PDF Export Error: {e}")
        return None

def prepare_csv(data_dict):
    """
    Przygotowuje bajty CSV dla download_button.
    """
    df = pd.DataFrame([data_dict])
    return df.to_csv(index=False).encode('utf-8-sig')